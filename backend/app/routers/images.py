import dataclasses
import logging
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel
from sqlalchemy import case, exists, func, or_, select
from sqlalchemy.orm import Session

from .. import storage
from ..db import SessionLocal
from ..models import B30Component, B30Result, DeviceResult, Image, OriginalFilename
from ..ocr.b30 import LAYOUTS
from ..ocr.layout_probe import ASPECT_TOLERANCE
from ..services import prefill

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/images", tags=["images"])

# image ids are immutable content addresses, so browsers can cache forever
_CACHE_IMMUTABLE = {"Cache-Control": "public, max-age=31536000, immutable"}


class ImageOut(BaseModel):
    id: str
    relative_path: str
    original_filename: str | None
    width: int | None
    height: int | None
    # classification by human-confirmed rows: which annotate flow this
    # image belongs to
    kind: str  # "device" | "b30" | "unclassified"
    # device: None = not annotated yet; otherwise device_results.checked.
    # b30: whether every component the layout expects is checked.
    checked: bool | None
    created_at: datetime

    @classmethod
    def of(
        cls,
        image: Image,
        original_filename: str | None,
        checked: bool | None,
        kind: str,
    ) -> "ImageOut":
        return cls(
            id=image.id,
            relative_path=image.relative_path,
            original_filename=original_filename,
            width=image.width,
            height=image.height,
            kind=kind,
            checked=checked,
            created_at=image.created_at.replace(tzinfo=UTC),
        )


class DeviceResultIn(BaseModel):
    rois_type: int | None = None
    song_id: str | None = None
    partner_id: str | None = None
    rating_class: int | None = None
    clear_status: int | None = None
    score: int | None = None
    pure: int | None = None
    far: int | None = None
    lost: int | None = None
    max_recall: int | None = None
    high_score: int | None = None
    high_score_delta: int | None = None
    pure_shiny: int | None = None
    pure_early: int | None = None
    pure_late: int | None = None
    far_early: int | None = None
    far_late: int | None = None
    checked: bool = False


class DeviceResultOut(DeviceResultIn):
    image_id: str
    updated_at: datetime


def _unchecked_filter():
    # a draft row (checked=false) counts as unchecked just like a missing row
    return ~exists(
        select(DeviceResult.image_id).where(
            DeviceResult.image_id == Image.id,
            DeviceResult.checked.is_(True),
        )
    )


class B30ComponentIn(BaseModel):
    index: int
    song_id: str | None = None
    rating_class: int | None = None
    score: int | None = None
    pure: int | None = None
    far: int | None = None
    lost: int | None = None
    pure_shiny: int | None = None
    clear_status: int | None = None
    checked: bool = False


class B30ResultIn(BaseModel):
    layout: str | None = None
    components: list[B30ComponentIn] = []


class B30ResultOut(BaseModel):
    layout: str | None
    components: list[B30ComponentIn]
    updated_at: datetime


def _b30_done_filter():
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


_KIND_FILTERS = {
    "device": exists(
        select(DeviceResult.image_id).where(DeviceResult.image_id == Image.id)
    ),
    "b30": exists(select(B30Result.image_id).where(B30Result.image_id == Image.id)),
    "unclassified": ~exists(
        select(DeviceResult.image_id).where(DeviceResult.image_id == Image.id)
    )
    & ~exists(select(B30Result.image_id).where(B30Result.image_id == Image.id)),
}


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


def _b30_done_map(session: Session, image_ids: list[str]) -> dict[str, bool | None]:
    """Whether each B30-classified image has every expected component
    checked; not-b30 images map to None."""
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
    result: dict[str, bool | None] = {}
    for image_id in image_ids:
        if image_id not in layouts:
            result[image_id] = None
            continue
        layout = layouts[image_id]
        expected = LAYOUTS.get(layout) if layout is not None else None
        result[image_id] = (
            expected is not None and counts.get(image_id, 0) >= expected.component_count
        )
    return result


def _kind_of(device_row_exists: bool, b30_row_exists: bool) -> str:
    if device_row_exists:
        return "device"
    if b30_row_exists:
        return "b30"
    return "unclassified"


@router.get("")
def list_images(
    offset: int = 0,
    limit: int = 50,
    unchecked_only: bool = False,
    kind: str | None = None,
) -> dict[str, object]:
    limit = min(limit, 200)
    with SessionLocal() as session:
        total = session.scalar(select(func.count(Image.id)))
        device_sq = (
            select(DeviceResult.image_id)
            .where(DeviceResult.image_id == Image.id)
            .exists()
        )
        b30_sq = (
            select(B30Result.image_id).where(B30Result.image_id == Image.id).exists()
        )
        stmt = select(
            Image,
            OriginalFilename.original_filename,
            select(DeviceResult.checked)
            .where(DeviceResult.image_id == Image.id)
            .scalar_subquery(),
            device_sq,
            b30_sq,
        ).outerjoin(OriginalFilename, OriginalFilename.image_id == Image.id)
        if kind is not None:
            if kind not in _KIND_FILTERS:
                raise HTTPException(status_code=422, detail=f"unknown kind: {kind}")
            stmt = stmt.where(_KIND_FILTERS[kind])
        if unchecked_only:
            if kind == "b30":
                stmt = stmt.where(_b30_done_filter())
            else:
                # device queue: a draft row (checked=false) counts as
                # unchecked just like a missing row; B30-classified images
                # belong to the B30 queue instead
                stmt = stmt.where(_unchecked_filter() & ~b30_sq)
        rows = session.execute(
            stmt.order_by(Image.created_at.desc()).offset(offset).limit(limit)
        ).all()
        done = _b30_done_map(session, [row[0].id for row in rows])
        items = []
        for image, original_filename, checked, has_device, has_b30 in rows:
            b30_done = done.get(image.id)
            checked_out = b30_done if has_b30 and not has_device else checked
            items.append(
                ImageOut.of(
                    image, original_filename, checked_out, _kind_of(has_device, has_b30)
                )
            )
        return {"total": total, "items": items}


@router.get("/b30_layouts")
def list_b30_layouts() -> list[dict[str, object]]:
    """Layout ids with their expected card counts, for the annotate UI."""
    return [
        {"id": layout.id, "component_count": layout.component_count}
        for layout in LAYOUTS.values()
    ]


def _require_image(session: Session, image_id: str) -> Image:
    image = session.get(Image, image_id)
    if image is None:
        raise HTTPException(status_code=404, detail="image not found")
    return image


@router.get("/{image_id}")
def get_image(image_id: str) -> ImageOut:
    with SessionLocal() as session:
        image = _require_image(session, image_id)
        provenance = session.get(OriginalFilename, image_id)
        has_device = session.get(DeviceResult, image_id) is not None
        has_b30 = session.get(B30Result, image_id) is not None
        checked_out: bool | None
        if has_b30:
            checked_out = _b30_done_map(session, [image_id])[image_id]
        else:
            checked_out = (
                session.scalar(
                    select(DeviceResult.checked).where(
                        DeviceResult.image_id == image_id
                    )
                )
                if has_device
                else None
            )
        return ImageOut.of(
            image,
            provenance.original_filename if provenance is not None else None,
            checked_out,
            _kind_of(has_device, has_b30),
        )


@router.get("/{image_id}/next")
def get_next_unchecked(image_id: str, kind: str = "device") -> dict[str, str | None]:
    """Next unchecked image in queue order (newest first), starting after
    `image_id` and wrapping to the queue head; `{"id": None}` when no
    unchecked image remains. The b30 queue also picks up images with no
    annotation rows whose aspect matches a known B30 canvas - aspect
    matches are verified with the structural probe, since 16:9 device
    screenshots share the arcaeaonline B50 canvas aspect."""
    if kind not in ("device", "b30"):
        raise HTTPException(status_code=422, detail=f"unknown kind: {kind}")
    with SessionLocal() as session:
        current = _require_image(session, image_id)
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
                _b30_done_filter() | (~device_sq & ~b30_sq & _b30_aspect_matches())
            )
            for scan_from in (after_current, None):
                stmt = queue.order_by(
                    Image.created_at.desc(), Image.id.desc()
                ).limit(_NEXT_SCAN_LIMIT)
                if scan_from is not None:
                    stmt = stmt.where(scan_from)
                for row_id, relative_path, has_b30_row in session.execute(stmt).all():
                    if has_b30_row or _probes_as_b30(row_id, relative_path):
                        return {"id": row_id}
            return {"id": None}
        queue = select(Image.id).where(
            _unchecked_filter()
            & ~exists(
                select(B30Result.image_id).where(B30Result.image_id == Image.id)
            )
        )
        queue = queue.order_by(Image.created_at.desc(), Image.id.desc())
        nxt = session.scalar(queue.where(after_current).limit(1))
        if nxt is None:
            nxt = session.scalar(queue.limit(1))
        return {"id": nxt}


@router.get("/{image_id}/prefill")
def get_prefill(image_id: str, flow: str | None = None) -> dict[str, object]:
    """Prefill for whichever flow the image probes as: the B30 layout id
    when it matches a B30 rendering, else the device OCR proposal.
    `flow=device` skips the probe and computes the device OCR proposal
    even for b30-probed images."""
    if flow not in (None, "device"):
        raise HTTPException(status_code=422, detail=f"unknown flow: {flow}")
    with SessionLocal() as session:
        image = _require_image(session, image_id)
        relative_path = image.relative_path
    try:
        if flow == "device":
            return {"kind": "device", "prefill": prefill.get(image_id, relative_path)}
        layout = prefill.b30_layout(image_id, relative_path)
        if layout is not None:
            return {"kind": "b30", "layout": layout}
        return {"kind": "device", "prefill": prefill.get(image_id, relative_path)}
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e


@router.get("/{image_id}/b30_prefill/{component_index}")
def get_b30_component_prefill(
    image_id: str, component_index: int, layout: str | None = None
) -> dict[str, object]:
    """OCR proposal for one card; 422 when the image does not probe as a
    supported B30 layout. `layout` overrides the probed layout."""
    if layout is not None and layout not in LAYOUTS:
        raise HTTPException(status_code=422, detail=f"unknown layout: {layout}")
    with SessionLocal() as session:
        image = _require_image(session, image_id)
        relative_path = image.relative_path
    try:
        result = prefill.b30_component(image_id, relative_path, component_index, layout)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    if result is None:
        raise HTTPException(status_code=422, detail="not a B30 screenshot")
    return dataclasses.asdict(result)


@router.get("/{image_id}/b30_card/{component_index}")
def get_b30_card(
    image_id: str, component_index: int, layout: str | None = None
) -> Response:
    if layout is not None and layout not in LAYOUTS:
        raise HTTPException(status_code=422, detail=f"unknown layout: {layout}")
    with SessionLocal() as session:
        image = _require_image(session, image_id)
        relative_path = image.relative_path
    try:
        jpeg = prefill.b30_card_jpeg(image_id, relative_path, component_index, layout)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    if jpeg is None:
        raise HTTPException(status_code=422, detail="not a B30 screenshot")
    return Response(content=jpeg, media_type="image/jpeg", headers=_CACHE_IMMUTABLE)


def _b30_result_out(session: Session, image_id: str) -> B30ResultOut | None:
    result = session.get(B30Result, image_id)
    if result is None:
        return None
    components = (
        session.query(B30Component)
        .filter(B30Component.image_id == image_id)
        .order_by(B30Component.component_index)
        .all()
    )
    return B30ResultOut(
        layout=result.layout,
        components=[
            B30ComponentIn(
                index=c.component_index,
                song_id=c.song_id,
                rating_class=c.rating_class,
                score=c.score,
                pure=c.pure,
                far=c.far,
                lost=c.lost,
                pure_shiny=c.pure_shiny,
                clear_status=c.clear_status,
                checked=c.checked,
            )
            for c in components
        ],
        updated_at=result.updated_at.replace(tzinfo=UTC),
    )


@router.get("/{image_id}/b30_result")
def get_b30_result(image_id: str) -> B30ResultOut | None:
    """Saved B30 annotation; `None` (HTTP 200) means not annotated yet."""
    with SessionLocal() as session:
        _require_image(session, image_id)
        return _b30_result_out(session, image_id)


@router.put("/{image_id}/b30_result")
def save_b30_result(image_id: str, body: B30ResultIn) -> B30ResultOut:
    with SessionLocal() as session:
        _require_image(session, image_id)
        if body.layout is not None and body.layout not in LAYOUTS:
            raise HTTPException(
                status_code=422, detail=f"unknown layout: {body.layout}"
            )
        result = session.get(B30Result, image_id)
        if result is None:
            result = B30Result(image_id=image_id)
        elif (
            body.layout is not None
            and result.layout is not None
            and result.layout != body.layout
        ):
            # stale rows of the old layout would count toward the new
            # one's completion
            session.query(B30Component).filter(
                B30Component.image_id == image_id
            ).delete()
        result.layout = body.layout
        session.add(result)
        for component in body.components:
            row = session.get(B30Component, (image_id, component.index))
            if row is None:
                row = B30Component(image_id=image_id, component_index=component.index)
            for field in (
                "song_id",
                "rating_class",
                "score",
                "pure",
                "far",
                "lost",
                "pure_shiny",
                "clear_status",
                "checked",
            ):
                setattr(row, field, getattr(component, field))
            session.add(row)
        session.commit()
        saved = _b30_result_out(session, image_id)
        assert saved is not None  # the row was just upserted
        return saved


@router.get("/{image_id}/result")
def get_result(image_id: str) -> DeviceResultOut | None:
    """Saved annotation; `None` (HTTP 200) means not annotated yet."""
    with SessionLocal() as session:
        _require_image(session, image_id)
        result = session.get(DeviceResult, image_id)
        if result is None:
            return None
        return DeviceResultOut(
            **{c: getattr(result, c) for c in DeviceResultIn.model_fields},
            image_id=image_id,
            updated_at=result.updated_at.replace(tzinfo=UTC),
        )


@router.put("/{image_id}/result")
def save_result(image_id: str, body: DeviceResultIn) -> DeviceResultOut:
    with SessionLocal() as session:
        _require_image(session, image_id)
        result = session.get(DeviceResult, image_id)
        if result is None:
            result = DeviceResult(image_id=image_id)
        for field in DeviceResultIn.model_fields:
            setattr(result, field, getattr(body, field))
        session.add(result)
        session.commit()
        return DeviceResultOut(
            **{c: getattr(result, c) for c in DeviceResultIn.model_fields},
            image_id=image_id,
            updated_at=result.updated_at.replace(tzinfo=UTC),
        )


@router.get("/{image_id}/thumb")
def get_thumbnail(image_id: str) -> FileResponse:
    path = storage.thumb_path_for(image_id)
    if not path.exists():
        raise HTTPException(status_code=404, detail="thumbnail not found")
    return FileResponse(path, media_type="image/jpeg", headers=_CACHE_IMMUTABLE)


@router.get("/{image_id}/file")
def get_original(image_id: str) -> FileResponse:
    with SessionLocal() as session:
        image = session.get(Image, image_id)
        if image is None:
            raise HTTPException(status_code=404, detail="image not found")
    path = storage.path_for(image.relative_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="file missing from storage")
    return FileResponse(path, headers=_CACHE_IMMUTABLE)
