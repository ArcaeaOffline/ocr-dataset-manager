from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from .. import storage
from ..db import SessionLocal
from ..models import DeviceResult, Image, OriginalFilename
from ..services import prefill

router = APIRouter(prefix="/api/images", tags=["images"])


class ImageOut(BaseModel):
    id: str
    relative_path: str
    original_filename: str | None
    width: int | None
    height: int | None
    has_thumbnail: bool
    # None = not annotated yet; otherwise the device_results.checked value
    checked: bool | None
    created_at: datetime

    @classmethod
    def of(
        cls,
        image: Image,
        original_filename: str | None,
        checked: bool | None,
    ) -> "ImageOut":
        return cls(
            id=image.id,
            relative_path=image.relative_path,
            original_filename=original_filename,
            width=image.width,
            height=image.height,
            has_thumbnail=storage.thumb_path_for(image.id).exists(),
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


@router.get("")
def list_images(
    offset: int = 0, limit: int = 50, unchecked_only: bool = False
) -> dict[str, object]:
    limit = min(limit, 200)
    with SessionLocal() as session:
        total = session.scalar(select(func.count(Image.id)))
        stmt = (
            select(
                Image,
                OriginalFilename.original_filename,
                DeviceResult.checked,
            )
            .outerjoin(OriginalFilename, OriginalFilename.image_id == Image.id)
            .outerjoin(DeviceResult, DeviceResult.image_id == Image.id)
        )
        if unchecked_only:
            stmt = stmt.where(
                or_(DeviceResult.checked.is_(None), DeviceResult.checked.is_(False))
            )
        rows = session.execute(
            stmt.order_by(Image.created_at.desc()).offset(offset).limit(limit)
        ).all()
        return {
            "total": total,
            "items": [ImageOut.of(*row) for row in rows],
        }


def _require_image(session: Session, image_id: str) -> Image:
    image = session.get(Image, image_id)
    if image is None:
        raise HTTPException(status_code=404, detail="image not found")
    return image


@router.get("/{image_id}/prefill")
def get_prefill(image_id: str) -> prefill.PrefillResult:
    with SessionLocal() as session:
        image = _require_image(session, image_id)
        relative_path = image.relative_path
    try:
        return prefill.get(image_id, relative_path)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e


@router.get("/{image_id}/result")
def get_result(image_id: str) -> DeviceResultOut:
    with SessionLocal() as session:
        _require_image(session, image_id)
        result = session.get(DeviceResult, image_id)
        if result is None:
            raise HTTPException(status_code=404, detail="not annotated yet")
        return DeviceResultOut(
            **{
                c: getattr(result, c)
                for c in DeviceResultIn.model_fields
            },
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
    return FileResponse(path, media_type="image/jpeg")


@router.get("/{image_id}/file")
def get_original(image_id: str) -> FileResponse:
    with SessionLocal() as session:
        image = session.get(Image, image_id)
        if image is None:
            raise HTTPException(status_code=404, detail="image not found")
    path = storage.path_for(image.relative_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="file missing from storage")
    return FileResponse(path)
