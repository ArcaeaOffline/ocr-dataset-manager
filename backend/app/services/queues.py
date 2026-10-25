"""Queue membership filters and the next-unchecked scan for the device
and B30 annotation queues."""

import logging
from typing import NamedTuple

from sqlalchemy import case, exists, func, or_, select
from sqlalchemy.orm import Session

from ..models import B30Component, B30Result, DeviceResult, Image
from ..ocr.b30 import LAYOUTS
from ..ocr.layout_probe import ASPECT_TOLERANCE
from . import prefill

logger = logging.getLogger(__name__)


def unchecked_filter():
    # a draft row (checked=false) counts as unchecked just like a missing row
    return ~exists(
        select(DeviceResult.image_id).where(
            DeviceResult.image_id == Image.id,
            DeviceResult.checked.is_(True),
        )
    )


def b30_done_filter():
    """Images classified as B30 whose components are not all checked; a
    B30 row whose layout is missing or unknown can never be done (the
    expected component count would be unknown)."""
    layout_sq = (
        select(B30Result.layout).where(B30Result.image_id == Image.id).scalar_subquery()
    )
    expected = case(
        *[
            (layout_sq == layout_id, layout.component_count)
            for layout_id, layout in LAYOUTS.items()
        ],
        else_=0,
    )
    checked_count = (
        select(func.count())
        .where(B30Component.image_id == Image.id, B30Component.checked.is_(True))
        .scalar_subquery()
    )
    return exists(select(B30Result.image_id).where(B30Result.image_id == Image.id)) & (
        layout_sq.is_(None)
        | layout_sq.not_in(list(LAYOUTS))
        | (checked_count < expected)
    )


KIND_FILTERS = {
    "device": exists(
        select(DeviceResult.image_id).where(DeviceResult.image_id == Image.id)
    ),
    "b30": exists(select(B30Result.image_id).where(B30Result.image_id == Image.id)),
    "unclassified": ~exists(
        select(DeviceResult.image_id).where(DeviceResult.image_id == Image.id)
    )
    & ~exists(select(B30Result.image_id).where(B30Result.image_id == Image.id)),
}


class B30Progress(NamedTuple):
    """Review progress of one B30-classified image; `expected` is None
    when the layout is missing or unknown, in which case the image can
    never be done."""

    checked: int
    expected: int | None

    @property
    def done(self) -> bool:
        return self.expected is not None and self.checked >= self.expected


def b30_progress_map(session: Session, image_ids: list[str]) -> dict[str, B30Progress]:
    """Review progress for each B30-classified image; images without a
    `b30_results` row are absent from the map."""
    if not image_ids:
        return {}
    layouts: dict[str, str | None] = {
        image_id: layout
        for image_id, layout in session.execute(
            select(B30Result.image_id, B30Result.layout).where(
                B30Result.image_id.in_(image_ids)
            )
        ).all()
    }
    counts: dict[str, int] = {
        image_id: count
        for image_id, count in session.execute(
            select(B30Component.image_id, func.count())
            .where(
                B30Component.image_id.in_(image_ids),
                B30Component.checked.is_(True),
            )
            .group_by(B30Component.image_id)
        ).all()
    }
    return {
        image_id: B30Progress(
            checked=counts.get(image_id, 0),
            expected=(
                LAYOUTS[layout].component_count
                if layout is not None and layout in LAYOUTS
                else None
            ),
        )
        for image_id, layout in layouts.items()
    }


def kind_of(device_row_exists: bool, b30_row_exists: bool) -> str:
    if device_row_exists:
        return "device"
    if b30_row_exists:
        return "b30"
    return "unclassified"


# the b30 next-image scan verifies aspect-matched candidates with the
# structural probe one by one; bound it so a queue head full of device
# screenshots (16:9 shares the arcaeaonline B50 aspect) cannot stall the
# request
_NEXT_SCAN_LIMIT = 50


def _probes_as_b30(image_id: str, relative_path: str) -> bool:
    try:
        return prefill.b30_layout(image_id, relative_path) is not None
    except Exception:
        logger.warning("b30 probe failed for %s", image_id, exc_info=True)
        return False


def _b30_aspect_matches():
    """SQL aspect gate over the known B30 canvases; NULL width/height (or
    height 0) yields NULL, which never matches."""
    aspect = Image.width * 1.0 / Image.height
    return or_(
        *[
            func.abs((aspect - w / h) / (w / h)) <= ASPECT_TOLERANCE
            for w, h in (layout.canvas for layout in LAYOUTS.values())
        ]
    )


def next_unchecked(session: Session, current: Image, kind: str) -> str | None:
    """Id of the next unchecked image in queue order (newest first),
    starting after `current` and wrapping to the queue head; None when no
    unchecked image remains. The b30 queue also picks up images with no
    annotation rows whose aspect matches a known B30 canvas - aspect
    matches are verified with the structural probe, since 16:9 device
    screenshots share the arcaeaonline B50 canvas aspect."""
    after_current = or_(
        Image.created_at < current.created_at,
        (Image.created_at == current.created_at) & (Image.id < current.id),
    )
    if kind == "b30":
        b30_sq = exists(
            select(B30Result.image_id).where(B30Result.image_id == Image.id)
        )
        device_sq = exists(
            select(DeviceResult.image_id).where(DeviceResult.image_id == Image.id)
        )
        queue = select(Image.id, Image.relative_path, b30_sq).where(
            b30_done_filter() | (~device_sq & ~b30_sq & _b30_aspect_matches())
        )
        for scan_from in (after_current, None):
            stmt = queue.order_by(
                Image.created_at.desc(), Image.id.desc()
            ).limit(_NEXT_SCAN_LIMIT)
            if scan_from is not None:
                stmt = stmt.where(scan_from)
            for row_id, relative_path, has_b30_row in session.execute(stmt).all():
                if has_b30_row or _probes_as_b30(row_id, relative_path):
                    return row_id
        return None
    queue = select(Image.id).where(
        unchecked_filter()
        & ~exists(select(B30Result.image_id).where(B30Result.image_id == Image.id))
    )
    queue = queue.order_by(Image.created_at.desc(), Image.id.desc())
    nxt = session.scalar(queue.where(after_current).limit(1))
    if nxt is None:
        nxt = session.scalar(queue.limit(1))
    return nxt
