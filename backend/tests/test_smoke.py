"""End-to-end smoke: the committed hand-drawn result screens through the
real OCR chain (RapidOCR + ihdb).

The PNGs are 100%-scale exports of the SVG sources next to them; after
re-export, update EXPECTED from the drawn values. Known gaps pinned as
None: device_t1_2's pure early/late (drawn as "(P30)(P19)" but not
recovered), and the T2 score-diff text defeats detection."""

import uuid
from pathlib import Path

import pytest

from app import storage
from app.config import IHDB_PATH

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"

# every field the fixtures draw; song/partner stay unasserted - the cover
# and partner blocks match ihdb by accident, not by design
EXPECTED: dict[str, dict[str, int | None]] = {
    "device_t1_1.png": {
        "rois_type": 0,
        "score": 9818358,
        "pure": 1248,
        "far": 29,
        "lost": 9,
        "max_recall": 604,
        "high_score": 9756125,
        "high_score_delta": 6233,
        "pure_shiny": 1096,
        "far_late": 15,
        "far_early": 14,
        "pure_late": 73,
        "pure_early": 79,
        "rating_class": 2,  # FUTURE
        "clear_status": 1,  # TRACK COMPLETE
    },
    "device_t1_2.png": {
        "rois_type": 0,
        "score": 9991186,
        "pure": 1020,
        "far": 2,
        "lost": 0,
        "max_recall": 1022,
        "high_score": 9971605,
        "high_score_delta": 19581,
        "pure_shiny": 971,
        "far_late": 2,
        "far_early": 0,
        "pure_late": None,
        "pure_early": None,
        "rating_class": 2,  # FUTURE
        "clear_status": 2,  # FULL RECALL
    },
    "device_t2_1.png": {
        "rois_type": 1,
        "score": 9988200,
        "pure": 1161,
        "far": 3,
        "lost": 0,
        "max_recall": 1164,
        "high_score": 9988209,
        "high_score_delta": None,
        "pure_shiny": 1087,
        "far_late": 0,
        "far_early": 3,
        "pure_late": 17,
        "pure_early": 57,
        "rating_class": 4,  # ETERNAL
        "clear_status": 2,  # FULL RECALL
    },
    "device_t2_2.png": {
        "rois_type": 1,
        "score": 9765820,
        "pure": 1397,
        "far": 26,
        "lost": 21,
        "max_recall": 672,
        "high_score": 9724262,
        "high_score_delta": None,
        "pure_shiny": 1278,
        "far_late": 9,
        "far_early": 17,
        "pure_late": 50,
        "pure_early": 69,
        "rating_class": 2,  # FUTURE
        "clear_status": 1,  # TRACK COMPLETE
    },
}

pytestmark = [
    pytest.mark.slow,
    pytest.mark.skipif(
        not IHDB_PATH.exists(),
        reason="ihdb file not present on this machine",
    ),
]


@pytest.mark.parametrize("fixture_name", sorted(EXPECTED))
def test_real_ocr_prefill_smoke(fixture_name: str) -> None:
    from app.services import prefill

    image_id = uuid.uuid4().hex
    relative_path, _, _ = storage.import_image(FIXTURES_DIR / fixture_name, image_id)

    result = prefill.get(image_id, relative_path)

    for key, expected_value in EXPECTED[fixture_name].items():
        assert result[key] == expected_value, f"{fixture_name}.{key}"
