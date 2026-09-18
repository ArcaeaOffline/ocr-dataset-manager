"""On-demand pre-annotation for device screenshots.

Everything computed here is ephemeral: an LRU cache keeps the last CAP
results in memory so flipping between recent images is instant, but
nothing is persisted - the database only stores human-affirmed values
(device_results). A cache miss simply recomputes (~1-2s/image)."""

import logging
import sqlite3
import threading
from collections import OrderedDict

import cv2
import numpy as np

from .. import storage
from ..config import IHDB_PATH
from ..ocr.rapid_ocr_provider import RapidOcrTextProvider

logger = logging.getLogger(__name__)

CAP = 100
CANDIDATE_COUNT = 5

_cache: OrderedDict[str, dict] = OrderedDict()
_cache_lock = threading.Lock()
# serializes OCR engine + ihdb access; single-user tool, throughput is
# irrelevant next to correctness. RLock: compute() holds it across the
# whole run while _get_text_provider() re-acquires it
_compute_lock = threading.RLock()

_text_provider: RapidOcrTextProvider | None = None


def _get_text_provider() -> RapidOcrTextProvider:
    global _text_provider
    with _compute_lock:
        if _text_provider is None:
            _text_provider = RapidOcrTextProvider(numeric_only=True)
        return _text_provider


def _read_int(text: str | None) -> int | None:
    if not text:
        return None
    try:
        return int(text)
    except ValueError:
        return None


def _mask_vote_counts(masker, roi, method_names: list[str]) -> list[int]:
    return [
        int(np.count_nonzero(getattr(masker, name)(roi))) for name in method_names
    ]


def _candidates_to_dicts(results) -> list[dict]:
    return [
        {"image_id": r.image_id, "confidence": r.confidence}
        for r in sorted(results, key=lambda r: r.confidence, reverse=True)[
            :CANDIDATE_COUNT
        ]
    ]


def compute(image_id: str, relative_path: str) -> dict:
    from arcaea_offline_ocr.crop import CropBlackEdges
    from arcaea_offline_ocr.providers import (
        ImageCategory,
        ImageHashDatabaseIdProvider,
    )
    from arcaea_offline_ocr.scenarios.device import (
        DeviceRoisExtractor,
        DeviceScenario,
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

        rois_type: int | None = None
        selector_result = DeviceRoisAutoSelector.select(cropped, None)
        if selector_result is DeviceRoisAutoSelectorResult.UNKNOWN:
            # layout undetectable; everything else stays empty
            return {"rois_type": None}
        if selector_result is DeviceRoisAutoSelectorResult.T1:
            rois_type = 0
        elif selector_result is DeviceRoisAutoSelectorResult.T2:
            rois_type = 1

        rois, masker = DeviceRoisAutoSelector.create_rois_and_masker(
            selector_result, cropped.shape[1], cropped.shape[0]
        )
        extractor = DeviceRoisExtractor(cropped, rois)
        provider = _get_text_provider()

        def text_int(roi) -> int | None:
            return _read_int(provider.result(roi))

        prefill: dict = {
            "rois_type": rois_type,
            "score": text_int(extractor.score),
            "pure": text_int(extractor.pure),
            "far": text_int(extractor.far),
            "lost": text_int(extractor.lost),
            "max_recall": text_int(extractor.max_recall),
            "rating_class_votes": _mask_vote_counts(
                masker,
                extractor.rating_class,
                [
                    "rating_class_pst",
                    "rating_class_prs",
                    "rating_class_ftr",
                    "rating_class_byd",
                    "rating_class_etr",
                ],
            ),
            "clear_status_votes": _mask_vote_counts(
                masker,
                extractor.clear_status,
                [
                    "clear_status_track_lost",
                    "clear_status_track_complete",
                    "clear_status_full_recall",
                    "clear_status_pure_memory",
                ],
            ),
        }
        prefill["rating_class"] = max(
            enumerate(prefill["rating_class_votes"]), key=lambda it: it[1]
        )[0]
        prefill["clear_status"] = max(
            enumerate(prefill["clear_status_votes"]), key=lambda it: it[1]
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


def get(image_id: str, relative_path: str) -> dict:
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
