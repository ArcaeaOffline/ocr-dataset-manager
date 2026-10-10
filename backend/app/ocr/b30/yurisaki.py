"""yurisaki B50 card recognition.

Card fields (canonical card is 390x135): jacket on the left, then title
with the difficulty color bar, the score, the "Potential a > b" line
ending in the clear badge, and the "P: n (+s) F: n L: n" counter line.
Cards render no partner, max recall, or early/late data."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from arcaea_offline_ocr.types import XYWHRect
from typing_extensions import override

from ..parsing import parse_int, parse_pure_shiny
from .base import (
    CLEAR_BADGE_LETTERS,
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
    jacket_rect = XYWHRect(20, 22, 92, 92)
    score_rect = XYWHRect(115, 45, 270, 33)
    # "Potential 10.7 > 12.8698  FR" - the badge is the trailing letters
    badge_rect = XYWHRect(280, 76, 105, 26)
    pure_rect = XYWHRect(113, 99, 118, 27)
    far_rect = XYWHRect(222, 99, 44, 27)
    lost_rect = XYWHRect(266, 99, 44, 27)
    difficulty_bar_rect = XYWHRect(121, 29, 8, 17)

    def __init__(self) -> None:
        from .base import YURISAKI_B50

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
        result = ComponentOcr(index=index)

        result.song_id, result.song_id_candidates = match_jacket(
            component_bgr, self.jacket_rect, providers.ihdb
        )

        result.score = parse_int(
            providers.text.result(crop_card(component_bgr, self.score_rect))
        )

        badge = providers.raw.result_rec_only(crop_card(component_bgr, self.badge_rect))
        result.clear_status = _badge_clear_status(badge)

        pure_text = providers.raw.result_rec_only(
            crop_card(component_bgr, self.pure_rect)
        )
        result.pure, result.pure_shiny = parse_pure_shiny(pure_text)
        result.far = providers.rec_only_int(crop_card(component_bgr, self.far_rect))
        result.lost = providers.rec_only_int(crop_card(component_bgr, self.lost_rect))

        rating, votes = vote_rating_class(
            crop_card(component_bgr, self.difficulty_bar_rect)
        )
        result.rating_class, result.rating_class_votes = rating, votes
        return result


def _badge_clear_status(text: str | None) -> int | None:
    if not text:
        return None
    letters = re.sub(r"[^A-Za-z]", "", text).upper()
    return CLEAR_BADGE_LETTERS.get(letters)
