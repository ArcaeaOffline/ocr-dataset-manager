"""Result-row lifecycle and the one-kind-per-image invariant.

A screenshot is either a device result screen or a bot B30/B50
rendering, never both: writing one kind's rows replaces the other
kind's in the same transaction. The annotate UI confirms before the
first cross-kind save; this module is the mechanical backstop.

Values arrive as plain mappings (the request models dumped by the
routers), keyed by the ORM column names they mirror; a component
mapping additionally carries `index`."""

from collections.abc import Mapping

from sqlalchemy import delete
from sqlalchemy.orm import Session

from ..models import B30Component, B30Result, DeviceResult


def save_device_result(
    session: Session, image_id: str, values: Mapping[str, object]
) -> DeviceResult:
    """Upsert the device_results row for `image_id`; every B30 row on
    the image (layout and cards) is dropped."""
    result = session.get(DeviceResult, image_id)
    if result is None:
        result = DeviceResult(image_id=image_id)
    for field, value in values.items():
        setattr(result, field, value)
    session.add(result)
    session.execute(delete(B30Result).where(B30Result.image_id == image_id))
    session.execute(delete(B30Component).where(B30Component.image_id == image_id))
    return result


def save_b30_result(
    session: Session,
    image_id: str,
    layout: str | None,
    components: list[Mapping[str, object]],
) -> None:
    """Upsert the b30_results row and the given component rows; component
    rows the payload omits stay untouched. Switching to a different
    non-null layout clears the old layout's components (stale rows would
    count toward the new layout's completion). The device_results row,
    if any, is dropped."""
    result = session.get(B30Result, image_id)
    if result is None:
        result = B30Result(image_id=image_id)
    elif layout is not None and result.layout is not None and result.layout != layout:
        session.execute(delete(B30Component).where(B30Component.image_id == image_id))
    result.layout = layout
    session.add(result)
    for component in components:
        data = dict(component)
        index = data.pop("index")
        assert isinstance(index, int)
        row = session.get(B30Component, (image_id, index))
        if row is None:
            row = B30Component(image_id=image_id, component_index=index)
        for field, value in data.items():
            setattr(row, field, value)
        session.add(row)
    session.execute(delete(DeviceResult).where(DeviceResult.image_id == image_id))
