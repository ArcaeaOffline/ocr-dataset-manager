import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def _new_uuid() -> str:
    return uuid.uuid4().hex


class Base(DeclarativeBase):
    pass


class ImportBatch(Base):
    __tablename__ = "import_batches"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_new_uuid)
    source_path: Mapped[str] = mapped_column(String, nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=lambda: datetime.now(UTC)
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    file_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    imported_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    skipped_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    note: Mapped[str | None] = mapped_column(String, nullable=True)


class Image(Base):
    __tablename__ = "images"
    __table_args__ = (Index("ix_images_sha256", "sha256", unique=True),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_new_uuid)
    # path relative to the images storage dir, e.g. "ab/ab3f....jpg"
    relative_path: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    original_filename: Mapped[str] = mapped_column(String, nullable=False)
    # nullable: backfilled on re-encounter for legacy migrated rows
    sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # whole-image perceptual hash (average hasher, 16x16), non-unique,
    # used only for "near-duplicate" warnings
    image_hash: Mapped[str | None] = mapped_column(String, nullable=True)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    import_batch_id: Mapped[str | None] = mapped_column(
        String(32), ForeignKey("import_batches.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=lambda: datetime.now(UTC)
    )
