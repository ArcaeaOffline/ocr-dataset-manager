"""yurisaki B50 card recognition.

Card fields (canonical card is 390x135): jacket on the left, then title
with the difficulty color bar, the score, the "Potential a > b" line
ending in the clear badge, and the "P: n (+s) F: n L: n" counter line.
Cards render no partner, max recall, or early/late data."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from typing_extensions import override

from ..parsing import parse_int, parse_pure_shiny
from .base import (
    CLEAR_BADGE_LETTERS,
    YURISAKI_B50,
    B30LayoutOcr,
    ComponentOcr,
    crop_card,
    match_jacket,
    vote_rating_class,
)

if TYPE_CHECKING:
    from cv2.typing import MatLike

    from .providers import OcrProviders


class YurisakiOcr(B30LayoutOcr):
    def __init__(self) -> None:
        self.layout = YURISAKI_B50

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

        def field(name: str) -> MatLike:
            rect = layout.field_rect_on_card(name, component_bgr)
            return crop_card(component_bgr, rect)

        result = ComponentOcr(index=index)

        result.song_id, result.song_id_candidates = match_jacket(
            component_bgr,
            layout.field_rect_on_card("jacket", component_bgr),
            providers.ihdb,
        )

        result.score = parse_int(providers.text.result(field("score")))

        # "Potential 10.7 > 12.8698  FR" - the badge is the trailing letters
        badge = providers.raw.result_rec_only(field("clear_badge"))
        result.clear_status = _badge_clear_status(badge)

        result.pure, result.pure_shiny = parse_pure_shiny(
            providers.raw.result_rec_only(field("pure"))
        )
        result.far = providers.rec_only_int(field("far"))
        result.lost = providers.rec_only_int(field("lost"))

        rating, votes = vote_rating_class(field("difficulty_bar"))
        result.rating_class, result.rating_class_votes = rating, votes
        return result


def _badge_clear_status(text: str | None) -> int | None:
    if not text:
        return None
    letters = re.sub(r"[^A-Za-z]", "", text).upper()
    return CLEAR_BADGE_LETTERS.get(letters)
