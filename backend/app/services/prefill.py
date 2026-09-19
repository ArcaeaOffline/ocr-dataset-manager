"""On-demand pre-annotation for device screenshots.

Everything computed here is ephemeral: an LRU cache keeps the last CAP
results in memory so flipping between recent images is instant, but
nothing is persisted - the database only stores human-affirmed values
(device_results). A cache miss simply recomputes (~1-2s/image)."""

import logging
import re
import sqlite3
import threading
from collections import OrderedDict
from collections.abc import Sequence
from typing import TYPE_CHECKING, TypeAlias

import cv2
import numpy as np
from arcaea_offline_ocr.crop import crop_xywh
from cv2.typing import MatLike

from .. import storage
from ..config import IHDB_PATH
from ..ocr.custom_rois import CustomRoisT1, CustomRoisT2
from ..ocr.rapid_ocr_provider import RapidOcrTextProvider

if TYPE_CHECKING:
    from arcaea_offline_ocr.providers import ImageIdProviderResult
    from arcaea_offline_ocr.scenarios.device.masker.auto import DeviceRoisMaskerAuto

logger = logging.getLogger(__name__)

CAP = 100
CANDIDATE_COUNT = 5

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


def _parse_int(text: str | None) -> int | None:
    if not text:
        return None
    digits = text.replace("'", "").replace(" ", "").lstrip("+")
    if not digits.isdigit():
        # rec sometimes renders lone digits as look-alike letters (O -> 0)
        digits = digits.translate(str.maketrans({"O": "0", "o": "0", "D": "0"}))
    return int(digits) if digits.isdigit() else None


def _parse_early_late(
    text: str | None, rois_type: int
) -> dict[str, int | None] | None:
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
    return [
        int(np.count_nonzero(getattr(masker, name)(roi))) for name in method_names
    ]


def _candidates_to_dicts(
    results: Sequence["ImageIdProviderResult"],
) -> list[dict[str, str | float]]:
    return [
        {"image_id": r.image_id, "confidence": r.confidence}
        for r in sorted(results, key=lambda r: r.confidence, reverse=True)[
            :CANDIDATE_COUNT
        ]
    ]


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
            return _parse_int(provider.result(roi))

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
            "high_score": _parse_int(
                raw_provider.result_rec_only(
                    crop_xywh(cropped, rois.high_score.rounded())
                )
            ),
            "high_score_delta": _parse_int(
                raw_provider.result_rec_only(
                    crop_xywh(cropped, rois.high_score_delta.rounded())
                )
            ),
            "pure_shiny": _parse_int(
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
        prefill["song_id"] = (
            max(jacket_candidates, key=lambda r: r.confidence).image_id
            if jacket_candidates
            else None
        )
        prefill["song_id_candidates"] = _candidates_to_dicts(jacket_candidates)
        prefill["partner_id"] = (
            max(partner_candidates, key=lambda r: r.confidence).image_id
            if partner_candidates
            else None
        )
        prefill["partner_id_candidates"] = _candidates_to_dicts(partner_candidates)
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
    for image_id, relative_path in image_ids_and_paths:
        try:
            get(image_id, relative_path)
        except Exception:
            logger.exception("prefill failed for %s", image_id)
