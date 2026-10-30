"""Characterization of the B30 layout registry: the JSON card tables and
field windows must reproduce the bots' rendered geometry, the probe must
classify synthetic images of each canvas, and the recognizers must
reference fields the JSON defines."""

import numpy as np
from arcaea_offline_ocr.providers import (
    ImageCategory,
    ImageHashDatabaseIdProvider,
)
from arcaea_offline_ocr.providers.ihdb import (
    ImageHashDatabaseIdProviderResult,
    ImageHashType,
)
from arcaea_offline_ocr.types import XYWHRect
from cv2.typing import MatLike
from typing_extensions import override

from app.ocr.b30 import LAYOUTS, RECOGNIZERS
from app.ocr.b30.base import (
    ARCAEAONLINE_B30,
    ARCAEAONLINE_B50,
    CHIERI_V4,
    YURISAKI_B50,
)
from app.ocr.b30.providers import OcrProviders
from app.ocr.layout_probe import probe
from app.ocr.rapid_ocr_provider import RapidOcrTextProvider


def test_registry_covers_every_recognizer() -> None:
    assert set(LAYOUTS) == {
        "yurisaki",
        "arcaeaonline_b30",
        "arcaeaonline_b50",
        "chieri_v4",
    }
    assert set(RECOGNIZERS) == set(LAYOUTS)


def test_component_counts() -> None:
    assert YURISAKI_B50.component_count == 50
    assert ARCAEAONLINE_B30.component_count == 30
    assert ARCAEAONLINE_B50.component_count == 50
    assert CHIERI_V4.component_count == 33


def test_first_and_last_card_rects_at_canonical_scale() -> None:
    assert list(YURISAKI_B50.component_rect(0, YURISAKI_B50.canvas)) == [
        15,
        420,
        390,
        135,
    ]
    assert list(YURISAKI_B50.component_rect(49, YURISAKI_B50.canvas)) == [
        1523,
        1545,
        390,
        135,
    ]
    assert list(ARCAEAONLINE_B30.component_rect(0, ARCAEAONLINE_B30.canvas)) == [
        58,
        340,
        330,
        250,
    ]
    assert list(ARCAEAONLINE_B30.component_rect(29, ARCAEAONLINE_B30.canvas)) == [
        1394,
        1700,
        330,
        250,
    ]
    assert list(ARCAEAONLINE_B50.component_rect(49, ARCAEAONLINE_B50.canvas)) == [
        1394,
        2788,
        330,
        250,
    ]
    assert list(CHIERI_V4.component_rect(32, CHIERI_V4.canvas)) == [
        1191,
        4010,
        502,
        240,
    ]


def test_field_windows_match_the_recognizers() -> None:
    assert list(YURISAKI_B50.field_rect("jacket", 1.0)) == [20, 22, 92, 92]
    assert list(YURISAKI_B50.field_rect("score", 1.0)) == [115, 45, 270, 33]
    assert list(YURISAKI_B50.field_rect("clear_badge", 1.0)) == [280, 76, 105, 26]
    assert list(YURISAKI_B50.field_rect("pure", 1.0)) == [113, 99, 118, 27]
    assert list(YURISAKI_B50.field_rect("far", 1.0)) == [222, 99, 44, 27]
    assert list(YURISAKI_B50.field_rect("lost", 1.0)) == [266, 99, 44, 27]
    assert list(YURISAKI_B50.field_rect("difficulty_bar", 1.0)) == [121, 29, 8, 17]
    assert list(YURISAKI_B50.field_rect("text_area", 1.0)) == [140, 35, 230, 60]

    assert list(ARCAEAONLINE_B30.field_rect("jacket", 1.0)) == [125, 25, 185, 170]
    assert list(ARCAEAONLINE_B30.field_rect("score", 1.0)) == [97, 160, 215, 35]
    assert list(ARCAEAONLINE_B30.field_rect("clear_badge", 1.0)) == [272, 178, 58, 62]
    assert list(ARCAEAONLINE_B30.field_rect("rank_badge", 1.0)) == [8, 22, 70, 45]
    # the B30 and B50 variants share one card design
    assert ARCAEAONLINE_B30.card_layout.fields == ARCAEAONLINE_B50.card_layout.fields


def test_rects_scale_with_image_width() -> None:
    half = (960, 875)
    assert list(YURISAKI_B50.component_rect(0, half)) == [7.5, 210.0, 195.0, 67.5]
    half_card = np.full((67, 195, 3), 255, dtype=np.uint8)
    assert list(YURISAKI_B50.field_rect_on_card("score", half_card)) == [
        57.5,
        22.5,
        135.0,
        16.5,
    ]


def _paint(img: np.ndarray, rect: tuple[int, int, int, int], value: int) -> None:
    x, y, w, h = rect
    img[y : y + h, x : x + w] = value


def test_probe_classifies_arcaeaonline_by_badge_and_strip() -> None:
    layout = ARCAEAONLINE_B30
    img = np.full((2092, 1800, 3), 30, dtype=np.uint8)
    for i in range(layout.component_count):
        card = layout.component_rect(i, layout.canvas)
        # rank badge: dark translucent panel with a white "#N" glyph whose
        # white fraction must land in [0.02, 0.30]
        badge = card + layout.field_rect("rank_badge", 1.0)
        _paint(img, badge.rounded(), 60)
        glyph = XYWHRect(badge.x, badge.y, badge.w, badge.h * 0.2)
        _paint(img, glyph.rounded(), 255)
        # score strip: dark band with white digits
        strip = card + layout.field_rect("score", 1.0)
        _paint(img, strip.rounded(), 20)
    guess = probe(img)
    assert guess is not None and guess.layout == "arcaeaonline_b30"


def test_probe_returns_none_for_unmatched_aspects() -> None:
    assert probe(np.full((600, 800, 3), 30, dtype=np.uint8)) is None


class _StubText(RapidOcrTextProvider):
    @override
    def __init__(self) -> None:  # pyright: ignore[reportMissingSuperCall]
        pass  # skip engine loading. Reads go through the stub methods

    @override
    def result(self, img: MatLike, /) -> str | None:
        return "123"

    @override
    def result_rec_only(self, img: MatLike, /) -> str | None:
        return "123"


class _StubIhdb(ImageHashDatabaseIdProvider):
    @override
    def __init__(self) -> None:  # pyright: ignore[reportMissingSuperCall]
        pass  # no database. Jacket lookups return no candidates

    @override
    def result(
        self,
        img: MatLike,
        category: ImageCategory,
        /,
        *,
        hash_type: ImageHashType = ImageHashType.DCT,
    ) -> ImageHashDatabaseIdProviderResult:
        return ImageHashDatabaseIdProviderResult(
            image_id="stub",
            category=category,
            confidence=0.0,
            image_hash_type=hash_type,
        )

    @override
    def results(
        self, img: MatLike, category: ImageCategory, /
    ) -> list[ImageHashDatabaseIdProviderResult]:
        return []


def test_recognizer_field_names_resolve() -> None:
    # blank cards with fixed stub outputs: a field name a recognizer
    # references but the layout JSON lacks raises KeyError here. Crop
    # positions are pinned by the golden tests above. chieri_v4 is
    # excluded - its field names live in core-ocr's own suite
    providers = OcrProviders(text=_StubText(), raw=_StubText(), ihdb=_StubIhdb())
    for layout_id in ("yurisaki", "arcaeaonline_b30", "arcaeaonline_b50"):
        recognizer = RECOGNIZERS[layout_id]()
        w, h = (round(v) for v in LAYOUTS[layout_id].card_size)
        card = np.full((h, w, 3), 200, dtype=np.uint8)
        result = recognizer.ocr_component(card, 0, providers)
        assert result.score == 123
