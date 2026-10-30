"""B30/B50 screenshot layout definitions.

Card geometry lives in JSON: `layouts/` beside this module, core-ocr's
packaged files for chieri_v4. All rects scale at runtime by
`factor = width / canvas_width` - bots render pixel-exact canvases, so
the height follows from the width."""

from __future__ import annotations

import json
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

import cv2
import numpy as np
from arcaea_offline_ocr.layouts import CardLayout, load_builtin_card_layout
from arcaea_offline_ocr.types import XYWHRect

if TYPE_CHECKING:
    from arcaea_offline_ocr.providers import ImageHashDatabaseIdProvider
    from cv2.typing import MatLike

    from .providers import OcrProviders

CANDIDATE_COUNT = 5


def crop_card(mat: MatLike, rect: XYWHRect) -> MatLike:
    """crop_xywh with the float-tolerant XYWHRect coerced to ints."""
    x, y, w, h = rect.rounded()
    return mat[y : y + h, x : x + w]


def _layouts_dir() -> Path:
    """Layout JSON location: beside this module in development, under the
    PyInstaller bundle root when frozen. Frozen code lives in the PYZ
    archive, so the data anchor is the bundle path odm.spec declares."""
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass is not None:
            return Path(meipass) / "app" / "ocr" / "b30" / "layouts"
    return Path(__file__).parent / "layouts"


@dataclass(frozen=True)
class B30Layout:
    id: str
    card_layout: CardLayout

    @property
    def canvas(self) -> tuple[int, int]:
        # (width, height) of the bot's canonical rendering
        return self.card_layout.canvas

    @property
    def card_size(self) -> tuple[float, float]:
        return self.card_layout.card_size

    @property
    def component_count(self) -> int:
        return self.card_layout.component_count

    def component_rect(self, index: int, size: tuple[int, int]) -> XYWHRect:
        """Card rect for `index` (zero-based, in JSON order) on an image
        of the given (width, height)."""
        return self.card_layout.card_rect(index, size[0] / self.canvas[0])

    def field_rect(self, field: str, factor: float) -> XYWHRect:
        return self.card_layout.field_rect(field, factor)

    def field_rect_on_card(self, field: str, component_bgr: MatLike) -> XYWHRect:
        """Card-local field window scaled against the cropped card's own
        width, so renders at non-canonical sizes stay aligned."""
        return self.card_layout.field_rect(
            field, component_bgr.shape[1] / self.card_size[0]
        )


@dataclass
class ComponentOcr:
    """OCR proposal for one card; every field is a suggestion the human
    confirms, so any of them may be None."""

    index: int
    song_id: str | None = None
    song_id_candidates: list[dict[str, str | float]] = field(default_factory=list)
    rating_class: int | None = None
    rating_class_votes: list[int] | None = None
    score: int | None = None
    pure: int | None = None
    far: int | None = None
    lost: int | None = None
    pure_shiny: int | None = None
    clear_status: int | None = None


# clear type as stored in play records; bots render the same states the
# st3 clearType byte does. Letter keys are the badge glyphs bots print.
CLEAR_BADGE_LETTERS: dict[str, int] = {
    "TL": 0,  # track lost
    "L": 0,
    "NC": 1,  # normal clear
    "TC": 1,
    "C": 1,
    "FR": 2,  # full recall
    "F": 2,
    "PM": 3,  # pure memory
    "EC": 4,  # easy clear
    "HC": 5,  # hard clear
}

# difficulty color votes. Ranges are the device masker's game-UI HSV
# values widened by a few hue degrees: bots re-render the same palette
# but shift it slightly (measured on yurisaki: FTR renders at hue 156
# against the device range's 149-155).
RATING_CLASS_HSV_RANGES: dict[
    int, tuple[tuple[int, int, int], tuple[int, int, int]]
] = {
    0: ((95, 40, 60), (110, 255, 255)),  # past
    1: ((40, 40, 75), (58, 190, 230)),  # present
    2: ((147, 25, 0), (163, 200, 255)),  # future
    3: ((165, 40, 40), (179, 255, 255)),  # beyond
    4: ((126, 50, 60), (145, 170, 220)),  # eternal
}


def vote_rating_class(roi_bgr: MatLike) -> tuple[int | None, list[int]]:
    """Color-vote a difficulty badge ROI. Returns (best_class, counts)
    with counts ordered pst, prs, ftr, byd, etr; best is None when every
    count is zero."""
    hsv = cv2.cvtColor(roi_bgr, cv2.COLOR_BGR2HSV)
    votes = [
        int(np.count_nonzero(cv2.inRange(hsv, lo, hi)))
        for lo, hi in RATING_CLASS_HSV_RANGES.values()
    ]
    if max(votes) == 0:
        return None, votes
    return max(range(len(votes)), key=votes.__getitem__), votes


# card jackets render ~96px square and sit a few px off between renders,
# enough to flip an ihdb match; sweeping small offsets and keeping each
# id's best confidence recovers the correct match
JACKET_OFFSETS: tuple[tuple[int, int], ...] = (
    (0, 0),
    (2, 2),
    (3, 3),
    (-2, -2),
    (2, 0),
    (0, 2),
)


def match_jacket(
    component_bgr: MatLike,
    jacket_rect: XYWHRect,
    ihdb: ImageHashDatabaseIdProvider,
) -> tuple[str | None, list[dict[str, str | float]]]:
    """Look a card's jacket up in the image hash database."""
    from arcaea_offline_ocr.providers import ImageCategory  # noqa: PLC0415

    results = []
    for dx, dy in JACKET_OFFSETS:
        rect = XYWHRect(
            jacket_rect.x + dx, jacket_rect.y + dy, jacket_rect.w, jacket_rect.h
        )
        roi = crop_card(component_bgr, rect)
        results.extend(
            ihdb.results(cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY), ImageCategory.JACKET)
        )
    by_id: dict[str, float] = {}
    for r in results:
        by_id[r.image_id] = max(by_id.get(r.image_id, 0.0), r.confidence)
    ranked = sorted(by_id.items(), key=lambda it: it[1], reverse=True)
    if not ranked:
        return None, []
    return ranked[0][0], [
        {"image_id": image_id, "confidence": confidence}
        for image_id, confidence in ranked[:CANDIDATE_COUNT]
    ]


class B30LayoutOcr(ABC):
    """Per-layout recognition: cut the cards out of the screenshot and
    propose values for each of them."""

    layout: B30Layout

    @abstractmethod
    def component_count(self) -> int: ...

    @abstractmethod
    def components(self, img: MatLike, providers: OcrProviders) -> list[MatLike]: ...

    @abstractmethod
    def ocr_component(
        self, component_bgr: MatLike, index: int, providers: OcrProviders
    ) -> ComponentOcr: ...


def _load_json_layout(id: str) -> B30Layout:
    data = json.loads((_layouts_dir() / f"{id}.json").read_text(encoding="utf-8"))
    return B30Layout(id, CardLayout.from_dict(data))


YURISAKI_B50 = _load_json_layout("yurisaki")

# one card design, two heights: the B30 variant renders 6 card rows, the
# B50 one 10; the header above and the footer below the grid are identical.
# The canvas height only feeds the aspect table - scaling is width-based.
ARCAEAONLINE_B30 = _load_json_layout("arcaeaonline_b30")
ARCAEAONLINE_B50 = _load_json_layout("arcaeaonline_b50")

CHIERI_V4 = B30Layout("chieri_v4", load_builtin_card_layout("chieri_v4"))
