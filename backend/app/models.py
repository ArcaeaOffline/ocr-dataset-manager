import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String
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
    failed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    note: Mapped[str | None] = mapped_column(String, nullable=True)


class Image(Base):
    __tablename__ = "images"
    __table_args__ = (Index("ix_images_sha256", "sha256", unique=True),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_new_uuid)
    # path relative to the images storage dir, e.g. "ab/ab3f....jpg"
    relative_path: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    # content hash, computed on every import; the basis of import dedup
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
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


class OriginalFilename(Base):
    """Provenance record: stored image uuid -> filename it arrived as.

    Kept out of `images` so the core table stays about the file itself,
    and so legacy uuid<-name CSVs can be loaded as-is."""

    __tablename__ = "image_original_filenames"

    image_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("images.id", ondelete="CASCADE"), primary_key=True
    )
    original_filename: Mapped[str] = mapped_column(String, nullable=False)


class DeviceResult(Base):
    """Annotated device-screenshot values, 1:1 with `images`.

    Only human-affirmed values live here; OCR prefill artifacts
    (candidates, confidences, mask votes) are recomputed on demand and
    never persisted."""

    __tablename__ = "device_results"

    image_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("images.id", ondelete="CASCADE"), primary_key=True
    )
    # 0 = T1, 1 = T2; this is itself annotated content, not metadata
    rois_type: Mapped[int | None] = mapped_column(Integer, nullable=True)
    song_id: Mapped[str | None] = mapped_column(String, nullable=True)
    partner_id: Mapped[str | None] = mapped_column(String, nullable=True)
    rating_class: Mapped[int | None] = mapped_column(Integer, nullable=True)
    clear_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pure: Mapped[int | None] = mapped_column(Integer, nullable=True)
    far: Mapped[int | None] = mapped_column(Integer, nullable=True)
    lost: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_recall: Mapped[int | None] = mapped_column(Integer, nullable=True)
    high_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    high_score_delta: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pure_shiny: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pure_early: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pure_late: Mapped[int | None] = mapped_column(Integer, nullable=True)
    far_early: Mapped[int | None] = mapped_column(Integer, nullable=True)
    far_late: Mapped[int | None] = mapped_column(Integer, nullable=True)
    checked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
