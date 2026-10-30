"""arcaeaonline card recognition, shared by the B30 and B50 variants.

Card fields (canonical card is 330x250): rank badge top-left, level
diamond top-right, jacket center, play potential and grade on the left
column, score strip at the bottom with the clear letter badge to its
right, title below the strip. The level diamond keeps one color across
difficulties, so cards render no rating class or P/F/L counters.
The score strip is white text over the jacket art, so detection-less
recognition is required (detection hallucinates digits from jacket
texture)."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from typing_extensions import override

from .base import (
    ARCAEAONLINE_B30,
    ARCAEAONLINE_B50,
    CLEAR_BADGE_LETTERS,
    B30Layout,
    B30LayoutOcr,
    ComponentOcr,
    crop_card,
    match_jacket,
)

if TYPE_CHECKING:
    from cv2.typing import MatLike

    from .providers import OcrProviders

_SINGLE_LETTERS = {"C": "NC", "F": "FR", "L": "TL"}


class ArcaeaonlineOcr(B30LayoutOcr):
    def __init__(self, layout: B30Layout) -> None:
        self.layout = layout

    @override
    def component_count(self) -> int:
        return self.layout.component_count

    @override
    def components(self, img: MatLike, providers: OcrProviders) -> list[MatLike]:
        size = (img.shape[1], img.shape[0])
        return [
            crop_card(img, self.layout.component_rect(i, size))
            for i in range(self.component_count())
        ]

    @override
    def ocr_component(
        self, component_bgr: MatLike, index: int, providers: OcrProviders
    ) -> ComponentOcr:
        layout = self.layout
        result = ComponentOcr(index=index)

        result.song_id, result.song_id_candidates = match_jacket(
            component_bgr,
            layout.field_rect_on_card("jacket", component_bgr),
            providers.ihdb,
        )

        score = crop_card(
            component_bgr, layout.field_rect_on_card("score", component_bgr)
        )
        result.score = providers.rec_only_int(score)

        # the clear letter sits in a heart-shaped badge right of the score
        letter = providers.raw.result_rec_only(
            crop_card(
                component_bgr, layout.field_rect_on_card("clear_badge", component_bgr)
            )
        )
        result.clear_status = _letter_clear_status(letter)
        return result


def _letter_clear_status(text: str | None) -> int | None:
    if not text:
        return None
    letters = re.sub(r"[^A-Za-z]", "", text).upper()
    letters = _SINGLE_LETTERS.get(letters, letters)
    return CLEAR_BADGE_LETTERS.get(letters)


class ArcaeaonlineB30Ocr(ArcaeaonlineOcr):
    def __init__(self) -> None:
        super().__init__(ARCAEAONLINE_B30)


class ArcaeaonlineB50Ocr(ArcaeaonlineOcr):
    def __init__(self) -> None:
        super().__init__(ARCAEAONLINE_B50)
