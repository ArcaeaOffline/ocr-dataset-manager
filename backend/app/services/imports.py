"""Folder import pipeline: scan -> sha256 dedup -> copy -> thumbnail +
perceptual hash. Runs in a daemon thread; progress lives in the
import_batches row and is meant to be polled over the API."""

import logging
import threading
import uuid
from datetime import UTC, datetime
from pathlib import Path

import cv2
from sqlalchemy import exists, select
from sqlalchemy.orm import Session

from .. import storage
from ..db import SessionLocal
from ..models import DeviceResult, Image, ImportBatch, OriginalFilename

logger = logging.getLogger(__name__)

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}

# stdlib uuid7 exists on 3.14+; uuid4 is the fallback there
_uuid7 = getattr(uuid, "uuid7", None)


def new_image_id() -> str:
    return (_uuid7() if _uuid7 else uuid.uuid4()).hex


def start_import(source_path: str, *, recursive: bool = False) -> str:
    root = Path(source_path)
    if not root.is_dir():
        msg = f"not a directory: {source_path}"
        raise NotADirectoryError(msg)

    with SessionLocal() as session:
        batch = ImportBatch(source_path=str(root.resolve()))
        session.add(batch)
        session.commit()
        batch_id = batch.id

    threading.Thread(
        target=_run,
        args=(batch_id, root, recursive),
        daemon=True,
        name=f"import-{batch_id[:8]}",
    ).start()
    return batch_id


def _scan(root: Path, recursive: bool) -> list[Path]:
    it = root.rglob("*") if recursive else root.iterdir()
    return sorted(p for p in it if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS)


def _run(batch_id: str, root: Path, recursive: bool) -> None:
    session = SessionLocal()
    try:
        batch = session.get(ImportBatch, batch_id)
        if batch is None:
            msg = f"import batch row missing: {batch_id}"
            raise RuntimeError(msg)
        files = _scan(root, recursive)
        batch.file_count = len(files)
        session.commit()

        imported: list[tuple[str, str]] = []
        for file in files:
            try:
                imported_one = _import_one(session, batch, file)
            except Exception:
                batch.failed_count += 1
                logger.exception("failed to import %s", file)
            else:
                if imported_one is not None:
                    imported.append(imported_one)
            session.commit()

        batch.finished_at = datetime.now(UTC)
        session.commit()
    finally:
        session.close()

    if not imported:
        return

    from . import prefill  # noqa: PLC0415

    # the prefill LRU only holds prefill.CAP entries, so warming more than
    # the head of the annotation queue is wasted OCR work
    with SessionLocal() as session:
        queue_head = session.execute(
            select(Image.id, Image.relative_path)
            .where(
                ~exists(
                    select(DeviceResult.image_id).where(
                        DeviceResult.image_id == Image.id,
                        DeviceResult.checked.is_(True),
                    )
                )
            )
            .order_by(Image.created_at.desc(), Image.id.desc())
            .limit(prefill.CAP)
        ).all()
    prefill.warm([(row[0], row[1]) for row in queue_head])


def _import_one(
    session: Session, batch: ImportBatch, file: Path
) -> tuple[str, str] | None:
    sha = storage.file_sha256(file)
    duplicate = session.scalar(select(Image).where(Image.sha256 == sha))
    if duplicate is not None:
        batch.skipped_count += 1
        return None

    image_id = new_image_id()
    relative_path, w, h = storage.import_image(file, image_id)
    img = cv2.imread(str(storage.path_for(relative_path)))
    if img is None:
        storage.path_for(relative_path).unlink()
        msg = f"copied file is not readable: {file}"
        raise ValueError(msg)
    storage.save_thumbnail(img, image_id)

    session.add(
        Image(
            id=image_id,
            relative_path=relative_path,
            sha256=sha,
            image_hash=storage.average_image_hash(img),
            width=w,
            height=h,
            import_batch_id=batch.id,
        )
    )
    session.add(OriginalFilename(image_id=image_id, original_filename=file.name))
    batch.imported_count += 1
    return image_id, relative_path
