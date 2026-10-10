"""Screenshot layout probing.

Decides which renderer produced an image before any OCR runs. Two
stages: an aspect-ratio gate over the known bot canvases (free - bots
render pixel-exact fixed sizes), then a per-candidate structural check
on card-interior statistics that do not depend on the screenshot's
background art. The 16:9 portrait device aspect (0.5625) collides with
arcaeaonline B50 (0.561), so that bucket tries the arcaeaonline check
first and falls through to the device ROIs selector.

Returns a guess only; the result is never persisted - the human-confirmed
layout lives in `b30_results.layout`."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

import cv2

from .b30.base import (
    ARCAEAONLINE_B30,
    ARCAEAONLINE_B50,
    CHIERI_V4,
    YURISAKI_B50,
    B30Layout,
)

if TYPE_CHECKING:
    from cv2.typing import MatLike

logger = logging.getLogger(__name__)

DEVICE = "device"

ASPECT_TOLERANCE = 0.02

# aspect ratios are width / height of the canonical canvases
_ASPECTS: dict[str, float] = {
    YURISAKI_B50.id: YURISAKI_B50.canvas[0] / YURISAKI_B50.canvas[1],
    ARCAEAONLINE_B30.id: ARCAEAONLINE_B30.canvas[0] / ARCAEAONLINE_B30.canvas[1],
    ARCAEAONLINE_B50.id: ARCAEAONLINE_B50.canvas[0] / ARCAEAONLINE_B50.canvas[1],
    "chieri_v4": CHIERI_V4.canvas[0] / CHIERI_V4.canvas[1],
}

# buckets whose aspect is shared with (or near) device screenshot aspects
# try their structural check first, then fall through to the device path
_DEVICE_COLLISIONS = frozenset({ARCAEAONLINE_B50.id})


@dataclass(frozen=True)
class LayoutGuess:
    layout: str  # a B30 layout id, or "device"
    aspect: float


def _white_fraction(img: MatLike, rect: tuple[int, int, int, int]) -> float:
    x, y, w, h = rect
    roi = img[y : y + h, x : x + w]
    if roi.size == 0:
        return -1.0
    return float((roi.min(axis=2) > 200).mean())


def _sample_rects(
    layout: B30Layout,
    size: tuple[int, int],
    rows: list[int],
    local: tuple[int, int, int, int],
) -> list[tuple[int, int, int, int]]:
    """Absolute rects of `local` (x, y, w, h in card-local canonical px)
    on a spread of grid positions, for probing without checking every
    card."""
    lx, ly, lw, lh = local
    factor = size[0] / layout.canvas[0]
    rects = []
    for row in rows:
        for col in {0, layout.cols // 2, layout.cols - 1}:
            card = layout.component_rect(row * layout.cols + col, size)
            rects.append(
                (
                    round(card.x + lx * factor),
                    round(card.y + ly * factor),
                    round(lw * factor),
                    round(lh * factor),
                )
            )
    return rects


def _check_yurisaki(img: MatLike) -> bool:
    layout = YURISAKI_B50
    size = (img.shape[1], img.shape[0])
    # card text area: white card background with dark text
    rects = _sample_rects(layout, size, rows=[0, 3, 7], local=(140, 35, 230, 60))
    fractions = [_white_fraction(img, r) for r in rects]
    return bool(fractions) and min(fractions) > 0.55


def _check_arcaeaonline(layout: B30Layout, img: MatLike) -> bool:
    size = (img.shape[1], img.shape[0])
    rows = [0, min(3, layout.rows - 1), layout.rows - 1]
    # rank badge: dark translucent panel with a small white "#N" glyph;
    # the panel brightness follows the background art, so only a wide
    # band is meaningful. Rejects white-card layouts outright.
    badge_rects = _sample_rects(layout, size, rows=rows, local=(8, 22, 70, 45))
    badge = [_white_fraction(img, r) for r in badge_rects]
    if not badge or not all(0.02 <= f <= 0.30 for f in badge):
        return False
    # score strip: dark band with white digits; translucent, but dark
    # stays dominant on every sampled background
    strip_rects = _sample_rects(layout, size, rows=rows, local=(97, 160, 215, 35))
    strips = []
    for x, y, w, h in strip_rects:
        roi = img[y : y + h, x : x + w]
        if roi.size == 0:
            return False
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        strips.append(float((gray < 90).mean()))
    return min(strips) > 0.35


# chieri renders card text over the jacket art, so no text-polarity
# statistic is stable between samples; its 1800x4400 canvas aspect is far
# from every phone aspect (21:9 is 4.7% away), so it is aspect-gated
# without a structural check. Layouts absent from here pass on aspect
# alone.
_CHECKS = {
    YURISAKI_B50.id: _check_yurisaki,
    ARCAEAONLINE_B30.id: lambda img: _check_arcaeaonline(ARCAEAONLINE_B30, img),
    ARCAEAONLINE_B50.id: lambda img: _check_arcaeaonline(ARCAEAONLINE_B50, img),
}


def _looks_like_device(img: MatLike) -> bool:
    from arcaea_offline_ocr.crop import CropBlackEdges  # noqa: PLC0415
    from arcaea_offline_ocr.scenarios.device.rois.selector import (  # noqa: PLC0415
        DeviceRoisAutoSelector,
        DeviceRoisAutoSelectorResult,
    )

    cropped = CropBlackEdges.crop_or_original(img)
    return (
        DeviceRoisAutoSelector.select(cropped, None)
        is not DeviceRoisAutoSelectorResult.UNKNOWN
    )


def probe(img: MatLike) -> LayoutGuess | None:
    """Classify a screenshot into a B30 layout or "device".

    None means no layout matched - the caller should treat the image as
    unclassified."""
    h, w = img.shape[:2]
    aspect = w / h
    candidates = [
        layout_id
        for layout_id, target in _ASPECTS.items()
        if abs(aspect - target) / target <= ASPECT_TOLERANCE
    ]
    # collision buckets defer to device unless their structural check passes
    candidates.sort(key=lambda c: c in _DEVICE_COLLISIONS)

    for layout_id in candidates:
        check = _CHECKS.get(layout_id)
        if check is None or check(img):
            return LayoutGuess(layout_id, aspect)

    if _looks_like_device(img):
        return LayoutGuess(DEVICE, aspect)
    return None
