"""Queue membership filters, category counts, and the adjacent-image
walk for the device and B30 annotation queues."""

import logging
from datetime import datetime
from typing import Literal, NamedTuple, TypedDict

from sqlalchemy import ColumnElement, case, exists, func, or_, select
from sqlalchemy.orm import InstrumentedAttribute, Session
from sqlalchemy.sql.elements import UnaryExpression

from ..models import B30Component, B30Result, DeviceResult, Image, OriginalFilename
from ..ocr.b30 import LAYOUTS
from ..ocr.layout_probe import ASPECT_TOLERANCE
from . import prefill

logger = logging.getLogger(__name__)

SortKey = Literal["created_at", "original_filename"]
SortDirection = Literal["asc", "desc"]
ImageCategory = Literal["all", "unchecked", "checked", "hidden"]
# the hidden category has no traversal: hidden images belong to no queue
AdjacentCategory = Literal["all", "unchecked", "checked"]
AdjacentFlow = Literal["device", "b30"]

QueueKind = Literal["device", "b30", "unclassified"]


def hidden_filter():
    """Hidden images belong to no annotation queue."""
    return Image.hidden.is_(False)


def unchecked_filter():
    # a draft row (checked=false) counts as unchecked just like a missing row
    return (
        ~exists(
            select(DeviceResult.image_id).where(
                DeviceResult.image_id == Image.id,
                DeviceResult.checked.is_(True),
            )
        )
        & hidden_filter()
    )


def b30_done_filter():
    """Images classified as B30 whose components are not all checked. A
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


def _device_sq() -> ColumnElement[bool]:
    return exists(
        select(DeviceResult.image_id).where(DeviceResult.image_id == Image.id)
    )


def _b30_sq() -> ColumnElement[bool]:
    return exists(select(B30Result.image_id).where(B30Result.image_id == Image.id))


KIND_FILTERS: dict[QueueKind, ColumnElement[bool]] = {
    "device": _device_sq() & hidden_filter(),
    "b30": _b30_sq() & hidden_filter(),
    "unclassified": ~_device_sq() & ~_b30_sq() & hidden_filter(),
}


def unchecked_view_filter(kind: QueueKind | None) -> ColumnElement[bool]:
    """Unchecked membership of a listing for the given kind display
    filter (None = every kind). A hybrid image presents as device
    (kind_of), so without the anti-joins the b30 disjuncts would pull
    checked device images into the unchecked views."""
    device_sq = _device_sq()
    b30_sq = _b30_sq()
    if kind == "b30":
        return b30_done_filter() & ~device_sq
    if kind is None:
        return (unchecked_filter() & ~b30_sq) | (b30_done_filter() & ~device_sq)
    # device queue: a draft row (checked=false) counts as unchecked just
    # like a missing row. B30-classified images belong to the B30 queue
    # instead
    return unchecked_filter() & ~b30_sq


class CategoryCounts(TypedDict):
    """Sidebar totals. all/unchecked/checked follow the kind filter and
    partition the visible set. Hidden ignores kind entirely."""

    all: int
    unchecked: int
    checked: int
    hidden: int


def count_categories(session: Session, kind: QueueKind | None) -> CategoryCounts:
    """Category totals for the queue sidebar. They reuse the listing's
    filter expressions, so counts and lists always agree."""
    visible: list[ColumnElement[bool]] = [hidden_filter()]
    if kind is not None:
        visible.append(KIND_FILTERS[kind])
    unchecked_view = unchecked_view_filter(kind)

    def _count(where: list[ColumnElement[bool]]) -> int:
        return (
            session.scalar(
                select(func.count(Image.id)).select_from(Image).where(*where)
            )
            or 0
        )

    return {
        "all": _count(visible),
        "unchecked": _count([*visible, unchecked_view]),
        "checked": _count([*visible, ~unchecked_view]),
        "hidden": _count([Image.hidden.is_(True)]),
    }


class B30Progress(NamedTuple):
    """Review progress of one B30-classified image. `expected` is None
    when the layout is missing or unknown, in which case the image can
    never be done."""

    checked: int
    expected: int | None

    @property
    def done(self) -> bool:
        return self.expected is not None and self.checked >= self.expected


def b30_progress_map(session: Session, image_ids: list[str]) -> dict[str, B30Progress]:
    """Review progress for each B30-classified image. Images without a
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


def kind_of(device_row_exists: bool, b30_row_exists: bool) -> QueueKind:
    if device_row_exists:
        return "device"
    if b30_row_exists:
        return "b30"
    return "unclassified"


# ---- ordering ------------------------------------------------------------


def order_exprs(
    order_by: SortKey, direction: SortDirection
) -> list[UnaryExpression[datetime] | UnaryExpression[str]]:
    """Shared ordering of the listing and the adjacent-image walk: the
    key column with NULLs always last (in both directions), tie-broken
    by the id in the same direction. Ids are unique, so the order is
    total and the walk's keyset comparisons are unambiguous."""
    key_column = (
        OriginalFilename.original_filename
        if order_by == "original_filename"
        else Image.created_at
    )
    if direction == "asc":
        return [key_column.asc().nulls_last(), Image.id.asc()]
    return [key_column.desc().nulls_last(), Image.id.desc()]


# ---- adjacent-image walk --------------------------------------------------

# the b30 next-image scan verifies aspect-matched candidates with the
# structural probe one by one. Bound it so a queue head full of device
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
    """SQL aspect gate over the known B30 canvases. NULL width/height (or
    height 0) yields NULL, which never matches."""
    aspect = Image.width * 1.0 / Image.height
    return or_(
        *[
            func.abs((aspect - w / h) / (w / h)) <= ASPECT_TOLERANCE
            for w, h in (layout.canvas for layout in LAYOUTS.values())
        ]
    )


def _b30_unchecked_core() -> ColumnElement[bool]:
    """Unchecked membership core of the b30 queue: incomplete b30 rows,
    plus rowless images whose aspect matches a known B30 canvas. Aspect
    matches are verified with the structural probe at walk time, since
    16:9 device screenshots share the arcaeaonline B50 canvas aspect."""
    device_sq = _device_sq()
    b30_sq = _b30_sq()
    return b30_done_filter() | (~device_sq & ~b30_sq & _b30_aspect_matches())


def _adjacent_queue_filter(
    flow: AdjacentFlow, category: AdjacentCategory
) -> ColumnElement[bool]:
    """Queue membership for the plain adjacent-image walk. Traversal
    follows the annotate flow, not the listing's kind display filter:
    the device flow also covers unclassified images (they are annotated
    in the device flow). The b30 unchecked queue additionally picks up
    rowless candidates, so it has its own walk in
    `_adjacent_b30_unchecked`."""
    device_sq = _device_sq()
    b30_sq = _b30_sq()
    if flow == "device":
        # device rows plus rowless images. Under the one-kind invariant
        # this equals ~b30_sq, but hybrids keep presenting as device
        gate = device_sq | ~b30_sq
        unchecked_core = ~exists(
            select(DeviceResult.image_id).where(
                DeviceResult.image_id == Image.id,
                DeviceResult.checked.is_(True),
            )
        )
    else:
        gate = b30_sq
        unchecked_core = _b30_unchecked_core()
    if category == "all":
        return hidden_filter() & gate
    if category == "unchecked":
        return hidden_filter() & gate & unchecked_core
    return hidden_filter() & gate & ~unchecked_core


def _key_column(
    order_by: SortKey,
) -> InstrumentedAttribute[datetime] | InstrumentedAttribute[str]:
    return (
        OriginalFilename.original_filename
        if order_by == "original_filename"
        else Image.created_at
    )


def _current_sort_key(
    session: Session, current: Image, order_by: SortKey
) -> datetime | str | None:
    if order_by == "original_filename":
        provenance = session.get(OriginalFilename, current.id)
        return provenance.original_filename if provenance is not None else None
    return current.created_at


def _after_current_expr(
    key_column: InstrumentedAttribute[datetime] | InstrumentedAttribute[str],
    current_id: str,
    current_key: datetime | str | None,
    direction: SortDirection,
    *,
    nullable: bool,
) -> ColumnElement[bool]:
    """Keyset condition selecting the entries strictly after the current
    image in the walk order (key column in `direction`, id tie-break in
    the same direction, NULLs always last - matching `order_exprs`)."""
    if current_key is None:
        # the current image sits in the NULL zone, which sorts last
        if direction == "asc":
            return key_column.is_(None) & (Image.id > current_id)
        return key_column.is_(None) & (Image.id < current_id)
    if direction == "asc":
        past = (key_column > current_key) | (
            (key_column == current_key) & (Image.id > current_id)
        )
    else:
        past = (key_column < current_key) | (
            (key_column == current_key) & (Image.id < current_id)
        )
    if nullable:
        # NULLs sort last, so every NULL key follows a non-null current key
        return past | key_column.is_(None)
    return past


def adjacent_image(
    session: Session,
    current: Image,
    flow: AdjacentFlow,
    category: AdjacentCategory,
    order_by: SortKey,
    direction: SortDirection,
) -> str | None:
    """Id of the adjacent image in queue order, starting after `current`
    and wrapping around the cycle (prev walks the reversed direction,
    which is the same cycle). None when the queue is empty. The current
    image only anchors the walk - it may lie outside the queue, e.g. a
    just-saved unchecked item. Ordering matches the listing."""
    if flow == "b30" and category == "unchecked":
        return _adjacent_b30_unchecked(session, current, order_by, direction)

    base = (
        select(Image.id)
        .outerjoin(OriginalFilename, OriginalFilename.image_id == Image.id)
        .where(_adjacent_queue_filter(flow, category))
        .order_by(*order_exprs(order_by, direction))
    )
    after = base.where(
        _after_current_expr(
            _key_column(order_by),
            current.id,
            _current_sort_key(session, current, order_by),
            direction,
            nullable=order_by == "original_filename",
        )
    )
    nxt = session.scalar(after.limit(1))
    if nxt is not None:
        return nxt
    # past the cycle's end the walk wraps back to its head
    return session.scalar(base.limit(1))


def _adjacent_b30_unchecked(
    session: Session,
    current: Image,
    order_by: SortKey,
    direction: SortDirection,
) -> str | None:
    """The b30 unchecked walk. Each of its two passes fetches at most
    `_NEXT_SCAN_LIMIT` queue candidates from the database and probes
    them one by one, so a head full of probe-refused device screenshots
    cannot stall the request."""
    base = (
        select(Image.id, Image.relative_path, _b30_sq())
        .outerjoin(OriginalFilename, OriginalFilename.image_id == Image.id)
        .where(hidden_filter() & _b30_unchecked_core())
        .order_by(*order_exprs(order_by, direction))
        .limit(_NEXT_SCAN_LIMIT)
    )
    after = base.where(
        _after_current_expr(
            _key_column(order_by),
            current.id,
            _current_sort_key(session, current, order_by),
            direction,
            nullable=order_by == "original_filename",
        )
    )
    # the first pass scans the candidates after the current one, the
    # wrap pass re-scans from the queue head
    for stmt in (after, base):
        for row_id, relative_path, has_b30_row in session.execute(stmt).all():
            if has_b30_row or _probes_as_b30(row_id, relative_path):
                return row_id
    return None
