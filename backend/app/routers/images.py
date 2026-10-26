import dataclasses
from datetime import UTC, datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel
from sqlalchemy import ColumnElement, func, select
from sqlalchemy.orm import Session

from .. import storage
from ..db import get_session
from ..models import B30Component, B30Result, DeviceResult, Image, OriginalFilename
from ..ocr.b30 import LAYOUTS
from ..services import prefill, queues, results

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
    kind: queues.QueueKind
    # device: None = not annotated yet; otherwise device_results.checked.
    # b30: whether every component the layout expects is checked.
    checked: bool | None
    # b30 only: reviewed card count and the layout's expected card count;
    # expected is None when the layout is missing or unknown
    b30_checked_count: int | None = None
    b30_component_count: int | None = None
    hidden: bool
    created_at: datetime

    @classmethod
    def of(
        cls,
        image: Image,
        original_filename: str | None,
        checked: bool | None,
        kind: queues.QueueKind,
        b30_progress: queues.B30Progress | None = None,
    ) -> "ImageOut":
        return cls(
            id=image.id,
            relative_path=image.relative_path,
            original_filename=original_filename,
            width=image.width,
            height=image.height,
            kind=kind,
            checked=checked,
            b30_checked_count=b30_progress.checked if b30_progress else None,
            b30_component_count=b30_progress.expected if b30_progress else None,
            hidden=image.hidden,
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


class ImageListOut(BaseModel):
    total: int
    items: list[ImageOut]


class HiddenIn(BaseModel):
    hidden: bool


class NextImageOut(BaseModel):
    id: str | None


class B30LayoutOut(BaseModel):
    id: str
    component_count: int


class PrefillCandidate(BaseModel):
    image_id: str
    confidence: float


# field-parity with PrefillResult in services/prefill.py; the OCR chain
# fills a subset per rois detectability, so every field but rois_type is
# optional and the endpoint serializes with exclude_unset
class PrefillPayload(BaseModel):
    rois_type: int | None
    score: int | None = None
    pure: int | None = None
    far: int | None = None
    lost: int | None = None
    max_recall: int | None = None
    rating_class: int | None = None
    rating_class_votes: list[int] | None = None
    clear_status: int | None = None
    clear_status_votes: list[int] | None = None
    high_score: int | None = None
    high_score_delta: int | None = None
    pure_shiny: int | None = None
    pure_early: int | None = None
    pure_late: int | None = None
    far_early: int | None = None
    far_late: int | None = None
    song_id: str | None = None
    song_id_candidates: list[PrefillCandidate] = []
    partner_id: str | None = None
    partner_id_candidates: list[PrefillCandidate] = []


class PrefillOut(BaseModel):
    kind: Literal["device", "b30"]
    layout: str | None = None
    prefill: PrefillPayload | None = None


class B30ComponentPrefillOut(BaseModel):
    index: int
    song_id: str | None = None
    song_id_candidates: list[PrefillCandidate] = []
    rating_class: int | None = None
    rating_class_votes: list[int] | None = None
    score: int | None = None
    pure: int | None = None
    far: int | None = None
    lost: int | None = None
    pure_shiny: int | None = None
    clear_status: int | None = None


@router.get("")
def list_images(
    # SQLite reads a negative LIMIT as unbounded and a negative OFFSET
    # as 0, so the lower bounds are enforced here rather than clamped
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1)] = 50,
    unchecked_only: bool = False,
    kind: queues.QueueKind | None = None,
    hidden: Literal["only"] | None = None,
    session: Session = Depends(get_session),
) -> ImageListOut:
    """`hidden` absent: exclude hidden images; `hidden=only`: list only
    hidden ones."""
    limit = min(limit, 200)
    hidden_condition = (
        Image.hidden.is_(False) if hidden is None else Image.hidden.is_(True)
    )
    device_sq = (
        select(DeviceResult.image_id).where(DeviceResult.image_id == Image.id).exists()
    )
    b30_sq = select(B30Result.image_id).where(B30Result.image_id == Image.id).exists()
    conditions: list[ColumnElement[bool]] = [hidden_condition]
    if kind is not None:
        conditions.append(queues.KIND_FILTERS[kind])
    if unchecked_only:
        # a hybrid image presents as device (queues.kind_of); without
        # ~device_sq the b30 disjuncts would pull checked device images
        # into the unchecked views
        if kind == "b30":
            conditions.append(queues.b30_done_filter() & ~device_sq)
        elif kind is None:
            conditions.append(
                (queues.unchecked_filter() & ~b30_sq)
                | (queues.b30_done_filter() & ~device_sq)
            )
        else:
            # device queue: a draft row (checked=false) counts as
            # unchecked just like a missing row; B30-classified images
            # belong to the B30 queue instead
            conditions.append(queues.unchecked_filter() & ~b30_sq)
    stmt = select(
        Image,
        OriginalFilename.original_filename,
        select(DeviceResult.checked)
        .where(DeviceResult.image_id == Image.id)
        .scalar_subquery(),
        device_sq,
        b30_sq,
    ).outerjoin(OriginalFilename, OriginalFilename.image_id == Image.id)
    if conditions:
        stmt = stmt.where(*conditions)
    # an unfiltered total desyncs pageCount whenever any filter is active
    total = session.scalar(
        select(func.count(Image.id)).select_from(Image).where(*conditions)
    )
    rows = session.execute(
        stmt.order_by(Image.created_at.desc()).offset(offset).limit(limit)
    ).all()
    progress = queues.b30_progress_map(session, [row[0].id for row in rows])
    items = []
    for image, original_filename, checked, has_device, has_b30 in rows:
        if has_b30 and not has_device:
            p = progress[image.id]
            checked_out: bool | None = p.done
            b30_progress = p
        else:
            checked_out = checked
            b30_progress = None
        items.append(
            ImageOut.of(
                image,
                original_filename,
                checked_out,
                queues.kind_of(has_device, has_b30),
                b30_progress,
            )
        )
    return ImageListOut(total=total or 0, items=items)


@router.get("/b30_layouts")
def list_b30_layouts() -> list[B30LayoutOut]:
    """Layout ids with their expected card counts, for the annotate UI."""
    return [
        B30LayoutOut(id=layout.id, component_count=layout.component_count)
        for layout in LAYOUTS.values()
    ]


def _require_image(session: Session, image_id: str) -> Image:
    image = session.get(Image, image_id)
    if image is None:
        raise HTTPException(status_code=404, detail="image not found")
    return image


def _image_out(session: Session, image: Image) -> ImageOut:
    provenance = session.get(OriginalFilename, image.id)
    has_device = session.get(DeviceResult, image.id) is not None
    has_b30 = session.get(B30Result, image.id) is not None
    checked_out: bool | None
    b30_progress: queues.B30Progress | None = None
    if has_b30 and not has_device:
        progress = queues.b30_progress_map(session, [image.id])[image.id]
        checked_out = progress.done
        b30_progress = progress
    else:
        checked_out = (
            session.scalar(
                select(DeviceResult.checked).where(DeviceResult.image_id == image.id)
            )
            if has_device
            else None
        )
    return ImageOut.of(
        image,
        provenance.original_filename if provenance is not None else None,
        checked_out,
        queues.kind_of(has_device, has_b30),
        b30_progress,
    )


@router.get("/{image_id}")
def get_image(image_id: str, session: Session = Depends(get_session)) -> ImageOut:
    return _image_out(session, _require_image(session, image_id))


@router.put("/{image_id}/hidden")
def set_image_hidden(
    image_id: str, body: HiddenIn, session: Session = Depends(get_session)
) -> ImageOut:
    """Hiding is reversible and idempotent; the row stays as a sha256
    dedup anchor, so re-importing the same file still counts as skipped."""
    image = _require_image(session, image_id)
    image.hidden = body.hidden
    session.commit()
    return _image_out(session, image)


@router.get("/{image_id}/next")
def get_next_unchecked(
    image_id: str,
    kind: Literal["device", "b30"] = "device",
    session: Session = Depends(get_session),
) -> NextImageOut:
    """Next unchecked image in queue order (newest first), starting after
    `image_id` and wrapping to the queue head; `{"id": None}` when no
    unchecked image remains."""
    current = _require_image(session, image_id)
    return NextImageOut(id=queues.next_unchecked(session, current, kind))


@router.get("/{image_id}/prefill", response_model_exclude_unset=True)
def get_prefill(
    image_id: str,
    flow: Literal["device"] | None = None,
    session: Session = Depends(get_session),
) -> PrefillOut:
    """Prefill for whichever flow the image probes as: the B30 layout id
    when it matches a B30 rendering, else the device OCR proposal.
    `flow=device` skips the probe and computes the device OCR proposal
    even for b30-probed images."""
    image = _require_image(session, image_id)
    relative_path = image.relative_path
    try:
        if flow == "device":
            payload = PrefillPayload.model_validate(
                prefill.get(image_id, relative_path)
            )
            return PrefillOut(kind="device", prefill=payload)
        layout = prefill.b30_layout(image_id, relative_path)
        if layout is not None:
            return PrefillOut(kind="b30", layout=layout)
        payload = PrefillPayload.model_validate(prefill.get(image_id, relative_path))
        return PrefillOut(kind="device", prefill=payload)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e


@router.get(
    "/{image_id}/b30_prefill/{component_index}", response_model_exclude_unset=True
)
def get_b30_component_prefill(
    image_id: str,
    component_index: int,
    layout: str | None = None,
    session: Session = Depends(get_session),
) -> B30ComponentPrefillOut:
    """OCR proposal for one card; 422 when the image does not probe as a
    supported B30 layout. `layout` overrides the probed layout."""
    if layout is not None and layout not in LAYOUTS:
        raise HTTPException(status_code=422, detail=f"unknown layout: {layout}")
    image = _require_image(session, image_id)
    relative_path = image.relative_path
    try:
        result = prefill.b30_component(image_id, relative_path, component_index, layout)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    if result is None:
        raise HTTPException(status_code=422, detail="not a B30 screenshot")
    return B30ComponentPrefillOut.model_validate(dataclasses.asdict(result))


@router.get(
    "/{image_id}/b30_card/{component_index}",
    response_class=FileResponse,
    responses={200: {"content": {"image/jpeg": {}}}},
)
def get_b30_card(
    image_id: str,
    component_index: int,
    layout: str | None = None,
    session: Session = Depends(get_session),
) -> Response:
    if layout is not None and layout not in LAYOUTS:
        raise HTTPException(status_code=422, detail=f"unknown layout: {layout}")
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
    components = session.scalars(
        select(B30Component)
        .where(B30Component.image_id == image_id)
        .order_by(B30Component.component_index)
    ).all()
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
def get_b30_result(
    image_id: str, session: Session = Depends(get_session)
) -> B30ResultOut | None:
    """Saved B30 annotation; `None` (HTTP 200) means not annotated yet."""
    _require_image(session, image_id)
    return _b30_result_out(session, image_id)


@router.put("/{image_id}/b30_result")
def save_b30_result(
    image_id: str, body: B30ResultIn, session: Session = Depends(get_session)
) -> B30ResultOut:
    _require_image(session, image_id)
    if body.layout is not None and body.layout not in LAYOUTS:
        raise HTTPException(status_code=422, detail=f"unknown layout: {body.layout}")
    results.save_b30_result(
        session, image_id, body.layout, [c.model_dump() for c in body.components]
    )
    session.commit()
    saved = _b30_result_out(session, image_id)
    assert saved is not None  # the row was just upserted
    return saved


@router.get("/{image_id}/result")
def get_result(
    image_id: str, session: Session = Depends(get_session)
) -> DeviceResultOut | None:
    """Saved annotation; `None` (HTTP 200) means not annotated yet."""
    _require_image(session, image_id)
    result = session.get(DeviceResult, image_id)
    if result is None:
        return None
    return _device_result_out(result)


def _device_result_out(result: DeviceResult) -> DeviceResultOut:
    return DeviceResultOut(
        **{c: getattr(result, c) for c in DeviceResultIn.model_fields},
        image_id=result.image_id,
        updated_at=result.updated_at.replace(tzinfo=UTC),
    )


@router.put("/{image_id}/result")
def save_result(
    image_id: str, body: DeviceResultIn, session: Session = Depends(get_session)
) -> DeviceResultOut:
    _require_image(session, image_id)
    result = results.save_device_result(session, image_id, body.model_dump())
    session.commit()
    return _device_result_out(result)


@router.get(
    "/{image_id}/thumb",
    response_class=FileResponse,
    responses={200: {"content": {"image/jpeg": {}}}},
)
def get_thumbnail(image_id: str) -> FileResponse:
    path = storage.thumb_path_for(image_id)
    if not path.exists():
        raise HTTPException(status_code=404, detail="thumbnail not found")
    return FileResponse(path, media_type="image/jpeg", headers=_CACHE_IMMUTABLE)


@router.get(
    "/{image_id}/file",
    response_class=FileResponse,
    responses={200: {"content": {"image/*": {}}}},
)
def get_original(
    image_id: str, session: Session = Depends(get_session)
) -> FileResponse:
    image = session.get(Image, image_id)
    if image is None:
        raise HTTPException(status_code=404, detail="image not found")
    path = storage.path_for(image.relative_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="file missing from storage")
    return FileResponse(path, headers=_CACHE_IMMUTABLE)
