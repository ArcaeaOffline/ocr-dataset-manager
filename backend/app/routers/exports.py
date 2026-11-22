from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import EXPORTS_DIR
from ..db import get_session
from ..models import Export
from ..services import exports as exports_service

router = APIRouter(prefix="/api/exports", tags=["exports"])


class ExportOut(BaseModel):
    id: str
    # directory and archive basename, from services.exports.export_name
    name: str
    started_at: datetime
    finished_at: datetime | None
    # image-level counters; crop-level breakdowns live in the export's
    # meta.json
    file_count: int
    exported_count: int
    skipped_count: int
    failed_count: int
    error: str | None

    @classmethod
    def of(cls, export: Export) -> "ExportOut":
        return cls(
            id=export.id,
            name=exports_service.export_name(export),
            started_at=export.started_at.replace(tzinfo=UTC),
            finished_at=(
                export.finished_at.replace(tzinfo=UTC) if export.finished_at else None
            ),
            file_count=export.file_count,
            exported_count=export.exported_count,
            skipped_count=export.skipped_count,
            failed_count=export.failed_count,
            error=export.error,
        )


@router.post("")
def create_export(session: Session = Depends(get_session)) -> ExportOut:
    try:
        export_id = exports_service.start_export()
    except exports_service.ExportRunningError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    export = session.get(Export, export_id)
    if export is None:
        raise HTTPException(status_code=404, detail="export not found")
    return ExportOut.of(export)


@router.get("")
def list_exports(session: Session = Depends(get_session)) -> list[ExportOut]:
    exports = session.scalars(
        select(Export).order_by(Export.started_at.desc()).limit(50)
    ).all()
    return [ExportOut.of(e) for e in exports]


@router.get("/{export_id}")
def get_export(export_id: str, session: Session = Depends(get_session)) -> ExportOut:
    export = session.get(Export, export_id)
    if export is None:
        raise HTTPException(status_code=404, detail="export not found")
    return ExportOut.of(export)


@router.get("/{export_id}/download")
def download_export(
    export_id: str, session: Session = Depends(get_session)
) -> FileResponse:
    export = session.get(Export, export_id)
    if export is None:
        raise HTTPException(status_code=404, detail="export not found")
    if export.finished_at is None:
        raise HTTPException(status_code=409, detail="export still running")
    name = exports_service.export_name(export)
    archive = EXPORTS_DIR / f"{name}.zip"
    if not archive.is_file():
        raise HTTPException(status_code=404, detail="export archive missing")
    return FileResponse(archive, media_type="application/zip", filename=f"{name}.zip")


@router.delete("/{export_id}", status_code=204)
def delete_export(export_id: str) -> None:
    try:
        exports_service.delete_export(export_id)
    except exports_service.ExportRunningError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
