from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..db import SessionLocal
from ..models import ImportBatch
from ..services import imports

router = APIRouter(prefix="/api/imports", tags=["imports"])


class ImportRequest(BaseModel):
    source_path: str
    recursive: bool = False


class ImportBatchOut(BaseModel):
    id: str
    source_path: str
    started_at: datetime
    finished_at: datetime | None
    file_count: int
    imported_count: int
    skipped_count: int
    failed_count: int

    @classmethod
    def of(cls, batch: ImportBatch) -> "ImportBatchOut":
        return cls(
            id=batch.id,
            source_path=batch.source_path,
            started_at=batch.started_at.replace(tzinfo=UTC),
            finished_at=(
                batch.finished_at.replace(tzinfo=UTC) if batch.finished_at else None
            ),
            file_count=batch.file_count,
            imported_count=batch.imported_count,
            skipped_count=batch.skipped_count,
            failed_count=batch.failed_count,
        )


@router.post("")
def create_import(req: ImportRequest) -> ImportBatchOut:
    try:
        batch_id = imports.start_import(req.source_path, recursive=req.recursive)
    except NotADirectoryError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    with SessionLocal() as session:
        batch = session.get(ImportBatch, batch_id)
        if batch is None:
            raise HTTPException(status_code=404, detail="batch not found")
        return ImportBatchOut.of(batch)


@router.get("")
def list_imports() -> list[ImportBatchOut]:
    with SessionLocal() as session:
        batches = (
            session.query(ImportBatch).order_by(ImportBatch.started_at.desc()).limit(50)
        )
        return [ImportBatchOut.of(b) for b in batches]


@router.get("/{batch_id}")
def get_import(batch_id: str) -> ImportBatchOut:
    with SessionLocal() as session:
        batch = session.get(ImportBatch, batch_id)
        if batch is None:
            raise HTTPException(status_code=404, detail="batch not found")
        return ImportBatchOut.of(batch)
