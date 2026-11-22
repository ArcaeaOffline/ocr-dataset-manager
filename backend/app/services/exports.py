"""Training-data export: confirmed device number ROIs to a
PyTorch-loadable directory. Runs in a daemon thread, like the import
pipeline. Progress lives in the exports row and is meant to be polled
over the API.

Scope is fixed by design: checked device results of visible images,
one ROI crop per filled number field plus the early/late line window.
"""

import importlib.metadata
import json
import logging
import shutil
import threading
import time
from collections import Counter
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, NotRequired, TypedDict

import cv2
from arcaea_offline_ocr.crop import crop_xywh
from cv2.typing import MatLike
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from ..config import EXPORTS_DIR
from ..db import SessionLocal
from ..models import DeviceResult, Export, Image
from . import display_format, prefill

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# progress commit cadence during the export loop. One commit per image
# costs an fsync apiece; pollers do not need that fidelity
_COMMIT_INTERVAL_SECONDS = 2.0


class ExportRunningError(Exception):
    """An unfinished export row exists, or the requested export is
    still running."""


class _SkipExport(Exception):
    """Expected per-image gap; `reason` is the meta.json skip-reason key."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class _Sample(TypedDict):
    """One manifest.jsonl line. Number fields carry `value`; the
    early/late line carries `value: None` plus its confirmed `values`."""

    image: str
    text: str
    value: int | None
    values: NotRequired[dict[str, int]]
    field: str
    rois_type: int
    source_image_id: str


# single-int number fields in manifest order, with typed accessors into
# the result row. early_late is exported separately as one window
_NUMBER_ATTRS: tuple[tuple[str, Callable[[DeviceResult], int | None]], ...] = (
    ("score", lambda r: r.score),
    ("high_score", lambda r: r.high_score),
    ("high_score_delta", lambda r: r.high_score_delta),
    ("pure", lambda r: r.pure),
    ("pure_shiny", lambda r: r.pure_shiny),
    ("far", lambda r: r.far),
    ("lost", lambda r: r.lost),
    ("max_recall", lambda r: r.max_recall),
)


def export_name(export: Export) -> str:
    """Directory and archive basename for one export: start timestamp
    prefix + row id, so exports sort by time in a file browser."""
    return f"{export.started_at:%Y%m%d_%H%M%S}_{export.id}"


def start_export() -> str:
    export = Export()
    with SessionLocal() as session:
        running = session.scalar(select(Export).where(Export.finished_at.is_(None)))
        if running is not None:
            msg = "an export is already running"
            raise ExportRunningError(msg)
        session.add(export)
        try:
            session.commit()
        except IntegrityError as e:
            # lost a concurrent start: uq_exports_single_running rejected
            # a second running row. The select above is only the fast path
            msg = "an export is already running"
            raise ExportRunningError(msg) from e
        export_id = export.id

    threading.Thread(
        target=_run,
        args=(export_id,),
        daemon=True,
        name=f"export-{export_id[:8]}",
    ).start()
    return export_id


def delete_export(export_id: str) -> None:
    with SessionLocal() as session:
        export = session.get(Export, export_id)
        if export is None:
            msg = f"export not found: {export_id}"
            raise LookupError(msg)
        if export.finished_at is None:
            msg = "export still running"
            raise ExportRunningError(msg)
        name = export_name(export)

        # files go first: a crash after the row delete would leave the
        # artifacts unreachable and uncollectable, while a leftover row
        # only retries cleanly ("archive missing")
        shutil.rmtree(EXPORTS_DIR / name, ignore_errors=True)
        (EXPORTS_DIR / f"{name}.zip").unlink(missing_ok=True)

        session.delete(export)
        session.commit()


def _run(export_id: str) -> None:
    session = SessionLocal()
    try:
        export = session.get(Export, export_id)
        if export is None:
            msg = f"export row missing: {export_id}"
            raise RuntimeError(msg)
        _export_all(session, export)
    except Exception as e:
        logger.exception("export %s failed", export_id)
        session.rollback()
        export = session.get(Export, export_id)
        if export is not None:
            export.error = f"{type(e).__name__}: {e}"
            export.finished_at = datetime.now(UTC)
            session.commit()
    finally:
        session.close()


def _export_all(session: "Session", export: Export) -> None:
    rows = session.execute(
        select(Image, DeviceResult)
        .join(DeviceResult, DeviceResult.image_id == Image.id)
        .where(DeviceResult.checked.is_(True), Image.hidden.is_(False))
        .order_by(Image.created_at, Image.id)
    ).all()
    export.file_count = len(rows)
    session.commit()

    out_dir = EXPORTS_DIR / export_name(export)
    rois_dir = out_dir / "rois"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "dataset.py").write_text(DATASET_PY, encoding="utf-8", newline="\n")

    skip_reasons: Counter[str] = Counter()
    per_field: Counter[str] = Counter()
    per_rois_type: Counter[int] = Counter()

    exported = skipped = failed = 0
    last_commit = time.monotonic()
    with (out_dir / "manifest.jsonl").open(
        "w", encoding="utf-8", newline="\n"
    ) as manifest:
        for image, result in rows:
            try:
                samples = _image_samples(rois_dir, image, result)
            except _SkipExport as skip:
                skipped += 1
                skip_reasons[skip.reason] += 1
            except Exception:
                session.rollback()
                failed += 1
                logger.exception("failed to export image %s", image.id)
            else:
                manifest.write("".join(json.dumps(s) + "\n" for s in samples))
                for sample in samples:
                    per_field[sample["field"]] += 1
                    per_rois_type[sample["rois_type"]] += 1
                exported += 1
            # the counters live in locals and overwrite the row wholesale:
            # the rollback above expires the ORM object, so incrementing
            # the row attributes directly would lose pending updates of
            # earlier images
            export.exported_count = exported
            export.skipped_count = skipped
            export.failed_count = failed
            if time.monotonic() - last_commit >= _COMMIT_INTERVAL_SECONDS:
                session.commit()
                last_commit = time.monotonic()
        # the tail counters are persisted before meta/zip: a job-level
        # failure below rolls the session back and must not lose them
        session.commit()

    _write_meta(out_dir, export, skip_reasons, per_field, per_rois_type)
    _write_readme(out_dir, export, per_field)
    shutil.make_archive(str(EXPORTS_DIR / export_name(export)), "zip", root_dir=out_dir)
    export.finished_at = datetime.now(UTC)
    session.commit()


def _image_samples(rois_dir: Path, image: Image, result: DeviceResult) -> list[_Sample]:
    """Crop and write the image's number ROIs. Returns one manifest
    sample per written crop. Raises _SkipExport for expected data gaps."""
    if result.rois_type is None:
        raise _SkipExport("rois_type_missing")
    rois_type = result.rois_type
    try:
        canvas = prefill.cropped_canvas(image.relative_path)
        rects = prefill.device_rois(image.relative_path, rois_type, canvas=canvas)[
            "rects"
        ]
    except ValueError:
        raise _SkipExport("file_unreadable") from None

    samples: list[_Sample] = []
    for field, value, sample_text in _number_samples(result):
        x, y, w, h = rects[field]
        crop = crop_xywh(canvas, (x, y, w, h))
        samples.append(
            {
                "image": f"rois/{_write_crop(rois_dir, image.id, field, crop)}",
                "text": sample_text,
                "value": value,
                "field": field,
                "rois_type": rois_type,
                "source_image_id": image.id,
            }
        )

    early_late = display_format.format_early_late(
        result.far_late, result.pure_late, result.far_early, result.pure_early
    )
    if early_late is not None:
        # mirror format_early_late: the far values are always present when
        # it renders; the pure parts appear together or not at all
        values: dict[str, int] = {}
        if result.far_late is not None:
            values["far_late"] = result.far_late
        if result.far_early is not None:
            values["far_early"] = result.far_early
        if result.pure_late is not None and result.pure_early is not None:
            values["pure_late"] = result.pure_late
            values["pure_early"] = result.pure_early
        x, y, w, h = rects["early_late"]
        crop = crop_xywh(canvas, (x, y, w, h))
        samples.append(
            {
                "image": f"rois/{_write_crop(rois_dir, image.id, 'early_late', crop)}",
                "text": early_late,
                "value": None,
                "values": values,
                "field": "early_late",
                "rois_type": rois_type,
                "source_image_id": image.id,
            }
        )
    return samples


def _number_samples(result: DeviceResult) -> list[tuple[str, int, str]]:
    """(field, value, text) for every number field the annotate view
    renders a preview for. Unfilled fields and fields with no preview
    (negative score) are omitted, mirroring the view."""
    samples = []
    for field, get_value in _NUMBER_ATTRS:
        value = get_value(result)
        if value is None:
            continue
        match field:
            case "score":
                text = display_format.format_score(value)
            case "high_score":
                text = display_format.format_high_score(value)
            case "high_score_delta":
                text = display_format.format_score_delta(value)
            case _:
                text = str(value)
        if text is not None:
            samples.append((field, value, text))
    return samples


def _write_crop(rois_dir: Path, image_id: str, field: str, crop: MatLike) -> str:
    """Encode one ROI crop as PNG under rois/. Returns its path relative
    to rois/."""
    ok, buf = cv2.imencode(".png", crop)
    if not ok:
        msg = f"failed to encode crop: {image_id} {field}"
        raise ValueError(msg)
    relative = f"{field}/{image_id[:2]}/{image_id}.png"
    dest = rois_dir / relative
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(buf.tobytes())
    return relative


def _write_meta(
    out_dir: Path,
    export: Export,
    skip_reasons: Counter[str],
    per_field: Counter[str],
    per_rois_type: Counter[int],
) -> None:
    """meta.json carries the job's operational record only: parameters
    were fixed, so the counters and versions identify what was produced."""
    meta = {
        "generated_at": datetime.now(UTC).isoformat(),
        "file_count": export.file_count,
        "exported_count": export.exported_count,
        "skipped_count": export.skipped_count,
        "failed_count": export.failed_count,
        "skip_reasons": dict(sorted(skip_reasons.items())),
        "per_field": dict(sorted(per_field.items())),
        "per_rois_type": {str(k): v for k, v in sorted(per_rois_type.items())},
        "versions": _versions(),
    }
    (out_dir / "meta.json").write_text(
        json.dumps(meta, indent=2) + "\n", encoding="utf-8", newline="\n"
    )


def _write_readme(out_dir: Path, export: Export, per_field: Counter[str]) -> None:
    """README.md orients the archive reader: what the bundled loader
    does and the export's counts."""
    if per_field:
        fields = "\n".join(
            f"  - {field}: {count}" for field, count in sorted(per_field.items())
        )
        counts = f"- 裁剪图共 {sum(per_field.values())} 张，明细如下\n{fields}"
    else:
        counts = "- 裁剪图共 0 张"

    # ruff: disable[E501]
    text = f"""# Arcaea 数字 ROI 训练集

ocr-dataset-manager device 标注导出，{export.started_at.replace(tzinfo=UTC).isoformat()}。

## 内容

- `rois/<field>/`: 结果页数字字段的原生分辨率 PNG 裁剪图。
- `manifest.jsonl`: 每行一个样本
  - `image`: 相对路径
  - `text`: 截图渲染文本
  - `value`: 整数真值（early/late 行为 null，改用 `values`）
  - 其他元数据，如 `field`、`rois_type`、`source_image_id`
- `meta.json`: 本次导出的运行计数与版本。
- `dataset.py`: 自包含的 PyTorch Dataset 加载脚本，仅依赖 torch 与 Pillow：

  ```python
  from dataset import RoiTextDataset

  dataset = RoiTextDataset(".")
  image, sample = dataset[0]
  ```

## 统计

导出 {export.exported_count} / 跳过 {export.skipped_count} / 失败 {export.failed_count}

{counts}
"""
    # ruff: enable[E501]
    (out_dir / "README.md").write_text(text, encoding="utf-8", newline="\n")


def _versions() -> dict[str, str | None]:
    def version(dist: str) -> str | None:
        try:
            return importlib.metadata.version(dist)
        except importlib.metadata.PackageNotFoundError:
            return None

    return {
        "odm_backend": version("odm-backend"),
        "arcaea_offline_ocr": version("arcaea-offline-ocr"),
    }


DATASET_PY = '''"""Self-contained loader for this export.

Requires torch and Pillow:

    from dataset import RoiTextDataset

    dataset = RoiTextDataset(".")
    image, sample = dataset[0]
"""

import json
from pathlib import Path

from PIL import Image
from torch.utils.data import Dataset


class RoiTextDataset(Dataset):
    """Number-ROI crops with the text the screenshot renders, as listed
    in manifest.jsonl. Returns (RGB image, sample dict)."""

    def __init__(self, root, transform=None):
        self.root = Path(root)
        self.transform = transform
        with (self.root / "manifest.jsonl").open(encoding="utf-8") as f:
            self.samples = [json.loads(line) for line in f]

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, index):
        sample = self.samples[index]
        image = Image.open(self.root / sample["image"]).convert("RGB")
        if self.transform is not None:
            image = self.transform(image)
        return image, sample
'''
