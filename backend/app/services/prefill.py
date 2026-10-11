"""On-demand pre-annotation for device screenshots and B30/B50 cards.

Everything computed here is ephemeral: LRU caches keep the last results
in memory so flipping between recent images is instant, but nothing is
persisted - the database only stores human-affirmed values
(device_results / b30_results / b30_components). A cache miss simply
recomputes (~0.4s per B50 card, ~1-2s per device image)."""

import logging
import re
import sqlite3
import threading
from collections import OrderedDict
from typing import TYPE_CHECKING, TypeAlias

import cv2
import numpy as np
from arcaea_offline_ocr.crop import crop_xywh
from cv2.typing import MatLike

from .. import storage
from ..config import IHDB_PATH
from ..ocr.b30 import B30LayoutOcr, ComponentOcr, make_recognizer
from ..ocr.b30.providers import OcrProviders
from ..ocr.custom_rois import CustomRoisT1, CustomRoisT2
from ..ocr.layout_probe import DEVICE, probe
from ..ocr.parsing import parse_int
from ..ocr.ranking import rank_candidates
from ..ocr.rapid_ocr_provider import RapidOcrTextProvider

if TYPE_CHECKING:
    from arcaea_offline_ocr.providers import ImageHashDatabaseIdProvider
    from arcaea_offline_ocr.scenarios.device.masker.auto import DeviceRoisMaskerAuto

logger = logging.getLogger(__name__)

CAP = 100

PrefillValue = int | str | None | list[int] | list[dict[str, str | float]]
PrefillResult: TypeAlias = dict[str, PrefillValue]
# T2 renders "L4(P36) E0(P16)": far_late (pure_late) far_early (pure_early);
# T1 only shows "L1 E5". Parens are optional because rec mangles them
_EARLY_LATE_T2 = re.compile(
    r"L\s*(\d+)\s*\(?\s*P?\s*(\d+)?\s*\)?\s*E\s*(\d+)\s*\(?\s*P?\s*(\d+)?\s*\)?",
    re.IGNORECASE,
)
_EARLY_LATE_T1 = re.compile(r"L\s*(\d+)\s*[-]?\s*E\s*(\d+)", re.IGNORECASE)

_cache: OrderedDict[str, PrefillResult] = OrderedDict()
_cache_lock = threading.Lock()
# serializes OCR engine + ihdb access; single-user tool, throughput is
# irrelevant next to correctness. RLock: compute() holds it across the
# whole run while _get_text_provider() re-acquires it
_compute_lock = threading.RLock()

_text_provider: RapidOcrTextProvider | None = None
_raw_text_provider: RapidOcrTextProvider | None = None


def _get_text_provider() -> RapidOcrTextProvider:
    global _text_provider
    with _compute_lock:
        if _text_provider is None:
            _text_provider = RapidOcrTextProvider(numeric_only=True)
        return _text_provider


def _get_raw_text_provider() -> RapidOcrTextProvider:
    """Keeps structure characters so early/late lines survive for regex;
    numeric-only normalization would collapse L0(P22) into 0220."""
    global _raw_text_provider
    with _compute_lock:
        if _raw_text_provider is None:
            _raw_text_provider = RapidOcrTextProvider(numeric_only=False)
        return _raw_text_provider


def _parse_early_late(text: str | None, rois_type: int) -> dict[str, int | None] | None:
    if not text:
        return None
    # rec renders the zero in "L0(P22)" as letter O more often than not
    normalized = text.replace("O", "0").replace("o", "0")
    if rois_type == 1:
        match = _EARLY_LATE_T2.search(normalized)
        if match is None:
            return None
        return {
            "far_late": int(match.group(1)),
            "pure_late": int(match.group(2)) if match.group(2) else None,
            "far_early": int(match.group(3)),
            "pure_early": int(match.group(4)) if match.group(4) else None,
        }
    match = _EARLY_LATE_T1.search(normalized)
    if match is None:
        return None
    return {"far_late": int(match.group(1)), "far_early": int(match.group(2))}


def _mask_vote_counts(
    masker: "DeviceRoisMaskerAuto", roi: MatLike, method_names: list[str]
) -> list[int]:
    return [int(np.count_nonzero(getattr(masker, name)(roi))) for name in method_names]


def compute(_image_id: str, relative_path: str) -> PrefillResult:
    from arcaea_offline_ocr.crop import CropBlackEdges
    from arcaea_offline_ocr.providers import (
        ImageCategory,
        ImageHashDatabaseIdProvider,
    )
    from arcaea_offline_ocr.scenarios.device import (
        DeviceRoisExtractor,
        DeviceScenario,
    )
    from arcaea_offline_ocr.scenarios.device.masker.auto import (
        DeviceRoisMaskerAutoT1,
        DeviceRoisMaskerAutoT2,
    )
    from arcaea_offline_ocr.scenarios.device.rois.selector import (
        DeviceRoisAutoSelector,
        DeviceRoisAutoSelectorResult,
    )

    with _compute_lock:
        img = cv2.imread(str(storage.path_for(relative_path)))
        if img is None:
            msg = f"stored file unreadable: {relative_path}"
            raise ValueError(msg)
        cropped = CropBlackEdges.crop_or_original(img)

        selector_result = DeviceRoisAutoSelector.select(cropped, None)
        if selector_result is DeviceRoisAutoSelectorResult.UNKNOWN:
            # layout undetectable; everything else stays empty
            return {"rois_type": None}
        if selector_result is DeviceRoisAutoSelectorResult.T1:
            rois_type = 0
            rois = CustomRoisT1(cropped.shape[1], cropped.shape[0])
            masker = DeviceRoisMaskerAutoT1()
        else:
            # only T1/T2 remain after the UNKNOWN early return
            rois_type = 1
            rois = CustomRoisT2(cropped.shape[1], cropped.shape[0])
            masker = DeviceRoisMaskerAutoT2()

        extractor = DeviceRoisExtractor(cropped, rois)
        provider = _get_text_provider()
        raw_provider = _get_raw_text_provider()

        def text_int(roi: MatLike) -> int | None:
            return parse_int(provider.result(roi))

        rating_class_votes = _mask_vote_counts(
            masker,
            extractor.rating_class,
            [
                "rating_class_pst",
                "rating_class_prs",
                "rating_class_ftr",
                "rating_class_byd",
                "rating_class_etr",
            ],
        )
        clear_status_votes = _mask_vote_counts(
            masker,
            extractor.clear_status,
            [
                "clear_status_track_lost",
                "clear_status_track_complete",
                "clear_status_full_recall",
                "clear_status_pure_memory",
            ],
        )
        prefill: PrefillResult = {
            "rois_type": rois_type,
            "score": text_int(extractor.score),
            "pure": text_int(extractor.pure),
            "far": text_int(extractor.far),
            "lost": text_int(extractor.lost),
            "max_recall": text_int(extractor.max_recall),
            "rating_class_votes": rating_class_votes,
            "clear_status_votes": clear_status_votes,
            "high_score": parse_int(
                raw_provider.result_rec_only(
                    crop_xywh(cropped, rois.high_score.rounded())
                )
            ),
            "high_score_delta": parse_int(
                raw_provider.result_rec_only(
                    crop_xywh(cropped, rois.high_score_delta.rounded())
                )
            ),
            "pure_shiny": parse_int(
                raw_provider.result_rec_only(
                    crop_xywh(cropped, rois.pure_shiny.rounded())
                )
            ),
        }

        early_late = _parse_early_late(
            raw_provider.result_rec_only(crop_xywh(cropped, rois.early_late.rounded())),
            rois_type,
        )
        if early_late is not None:
            prefill.update(early_late)
        for key in ("far_late", "pure_late", "far_early", "pure_early"):
            prefill.setdefault(key, None)
        prefill["rating_class"] = max(
            enumerate(rating_class_votes), key=lambda it: it[1]
        )[0]
        prefill["clear_status"] = max(
            enumerate(clear_status_votes), key=lambda it: it[1]
        )[0]

        with sqlite3.connect(IHDB_PATH) as conn:
            ihdb = ImageHashDatabaseIdProvider(conn)
            jacket_candidates = ihdb.results(
                cv2.cvtColor(extractor.jacket, cv2.COLOR_BGR2GRAY),
                ImageCategory.JACKET,
            )
            partner_candidates = ihdb.results(
                DeviceScenario.preprocess_char_icon(
                    cv2.cvtColor(extractor.partner_icon, cv2.COLOR_BGR2GRAY),
                ),
                ImageCategory.PARTNER_ICON,
            )
        prefill["song_id"], prefill["song_id_candidates"] = rank_candidates(
            jacket_candidates
        )
        prefill["partner_id"], prefill["partner_id_candidates"] = rank_candidates(
            partner_candidates
        )
        return prefill


def get(image_id: str, relative_path: str) -> PrefillResult:
    with _cache_lock:
        if image_id in _cache:
            _cache.move_to_end(image_id)
            return _cache[image_id]

    result = compute(image_id, relative_path)

    with _cache_lock:
        _cache[image_id] = result
        _cache.move_to_end(image_id)
        while len(_cache) > CAP:
            _cache.popitem(last=False)
    return result


def warm(image_ids_and_paths: list[tuple[str, str]]) -> None:
    """Warm the cache head of the annotation queue: full device prefill
    for device-shaped images, layout probe only for B30/B50 ones (their
    cards are too expensive to precompute in bulk)."""
    for image_id, relative_path in image_ids_and_paths:
        try:
            img = cv2.imread(str(storage.path_for(relative_path)))
            if img is None:
                continue
            guess = probe(img)
            if guess is not None and guess.layout != DEVICE:
                b30_layout(image_id, relative_path)
            else:
                get(image_id, relative_path)
        except Exception:
            logger.exception("prefill failed for %s", image_id)


# ---- B30/B50 ------------------------------------------------------------
# layout guess per image, then one OCR pass per card. Cards are expensive
# (~0.4s each, 50 per screenshot), so they are only computed on request -
# never warmed in bulk.

_b30_layouts: OrderedDict[str, str | None] = OrderedDict()
_b30_components: OrderedDict[tuple[str, str, int], ComponentOcr] = OrderedDict()
_ihdb: "ImageHashDatabaseIdProvider | None" = None


def _read_image(relative_path: str) -> MatLike:
    img = cv2.imread(str(storage.path_for(relative_path)))
    if img is None:
        msg = f"stored file unreadable: {relative_path}"
        raise ValueError(msg)
    return img


def _get_ihdb():
    """One shared connection; all ihdb access runs under `_compute_lock`,
    so `check_same_thread=False` is safe."""
    global _ihdb
    with _compute_lock:
        if _ihdb is None:
            from arcaea_offline_ocr.providers import (
                ImageHashDatabaseIdProvider,  # noqa: PLC0415
            )

            conn = sqlite3.connect(IHDB_PATH, check_same_thread=False)
            _ihdb = ImageHashDatabaseIdProvider(conn)
        return _ihdb


_providers: OcrProviders | None = None


def _get_providers() -> OcrProviders:
    # one bundle, so chieri's scenario cache (keyed on provider identity)
    # survives across requests
    global _providers
    with _compute_lock:
        if _providers is None:
            _providers = OcrProviders(
                text=_get_text_provider(),
                raw=_get_raw_text_provider(),
                ihdb=_get_ihdb(),
            )
        return _providers


_recognizers: dict[str, B30LayoutOcr] = {}


def _get_recognizer(layout_id: str) -> B30LayoutOcr:
    # singletons; callers run under _compute_lock
    recognizer = _recognizers.get(layout_id)
    if recognizer is None:
        recognizer = make_recognizer(layout_id)
        _recognizers[layout_id] = recognizer
    return recognizer


def b30_layout(image_id: str, relative_path: str) -> str | None:
    """Probe the bot layout of a screenshot; None when it is a device
    screenshot or nothing matches."""
    with _cache_lock:
        if image_id in _b30_layouts:
            return _b30_layouts[image_id]

    guess = probe(_read_image(relative_path))
    layout = guess.layout if guess is not None and guess.layout != DEVICE else None

    with _cache_lock:
        _b30_layouts[image_id] = layout
        _b30_layouts.move_to_end(image_id)
        while len(_b30_layouts) > CAP:
            _b30_layouts.popitem(last=False)
    return layout


def b30_component(
    image_id: str,
    relative_path: str,
    index: int,
    layout_id: str | None = None,
) -> ComponentOcr | None:
    """OCR one card of a B30/B50 screenshot. `layout_id` overrides the
    probed layout; None is returned when no layout is given and the image
    does not probe as a supported B30 layout."""
    if layout_id is None:
        layout_id = b30_layout(image_id, relative_path)
        if layout_id is None:
            return None

    cache_key = (image_id, layout_id, index)
    with _cache_lock:
        cached = _b30_components.get(cache_key)
    if cached is not None:
        with _cache_lock:
            _b30_components.move_to_end(cache_key)
        return cached

    with _compute_lock:
        recognizer = _get_recognizer(layout_id)
        providers = _get_providers()
        img = _read_image(relative_path)
        cards = recognizer.components(img, providers)
        if not 0 <= index < len(cards):
            msg = f"component index out of range: {index}"
            raise ValueError(msg)
        result = recognizer.ocr_component(cards[index], index, providers)

    with _cache_lock:
        _b30_components[cache_key] = result
        _b30_components.move_to_end(cache_key)
        while len(_b30_components) > CAP:
            _b30_components.popitem(last=False)
    return result


def b30_card_jpeg(
    image_id: str,
    relative_path: str,
    index: int,
    layout_id: str | None = None,
) -> bytes | None:
    """JPEG-encoded crop of one card, for the annotate view. `layout_id`
    overrides the probed layout; None is returned when no layout is given
    and the image does not probe as a supported B30 layout."""
    if layout_id is None:
        layout_id = b30_layout(image_id, relative_path)
        if layout_id is None:
            return None

    with _compute_lock:
        recognizer = _get_recognizer(layout_id)
        img = _read_image(relative_path)
        cards = recognizer.components(img, _get_providers())
        if not 0 <= index < len(cards):
            msg = f"component index out of range: {index}"
            raise ValueError(msg)
        ok, buf = cv2.imencode(".jpg", cards[index])
        if not ok:
            msg = f"failed to encode card image: {image_id}#{index}"
            raise ValueError(msg)
        return buf.tobytes()
