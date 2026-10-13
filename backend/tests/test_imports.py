import shutil
import time
from collections.abc import Iterator
from pathlib import Path

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app import storage
from app.config import DATA_DIR
from app.db import SessionLocal
from app.models import Image, OriginalFilename

# same field set as ImportBatch in frontend/src/api.ts - the wire contract
IMPORT_BATCH_KEYS = {
    "id",
    "source_path",
    "started_at",
    "finished_at",
    "file_count",
    "imported_count",
    "skipped_count",
    "failed_count",
}


def _write_png(path: Path, fill: int) -> None:
    assert cv2.imwrite(str(path), np.full((48, 32, 3), fill, dtype=np.uint8))


def _wait_finished(
    client: TestClient, batch_id: str, timeout_s: float = 15.0
) -> dict[str, object]:
    """start_import runs the pipeline in a daemon thread; poll the batch
    row until it carries finished_at."""
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        response = client.get(f"/api/imports/{batch_id}")
        assert response.status_code == 200
        body = response.json()
        if body["finished_at"] is not None:
            return body
        time.sleep(0.05)
    pytest.fail(f"import batch {batch_id} did not finish within {timeout_s}s")


def _start_and_wait(
    client: TestClient, source: Path, *, recursive: bool = False
) -> dict[str, object]:
    response = client.post(
        "/api/imports", json={"source_path": str(source), "recursive": recursive}
    )
    assert response.status_code == 200
    return _wait_finished(client, response.json()["id"])


@pytest.fixture
def source_dir(tmp_path: Path) -> Iterator[Path]:
    source = tmp_path / "src"
    source.mkdir()
    yield source


def test_import_lifecycle(client: TestClient, source_dir: Path) -> None:
    for i, fill in enumerate((10, 20, 30)):
        _write_png(source_dir / f"img{i}.png", fill)

    response = client.post("/api/imports", json={"source_path": str(source_dir)})
    assert response.status_code == 200
    batch = response.json()
    assert set(batch) == IMPORT_BATCH_KEYS

    batch = _wait_finished(client, batch["id"])
    assert batch["file_count"] == 3
    assert batch["imported_count"] == 3
    assert batch["skipped_count"] == 0
    assert batch["failed_count"] == 0
    assert any(b["id"] == batch["id"] for b in client.get("/api/imports").json())

    with SessionLocal() as session:
        images = session.scalars(select(Image)).all()
        assert len(images) == 3
        for image in images:
            assert image.width == 32
            assert image.height == 48
            assert image.relative_path == storage.relative_path_for(image.id, ".png")
            assert storage.path_for(image.relative_path).is_file()
            assert storage.thumb_path_for(image.id).is_file()
            provenance = session.get(OriginalFilename, image.id)
            assert provenance is not None
        names = {
            p.original_filename for p in session.scalars(select(OriginalFilename))
        }
        assert names == {"img0.png", "img1.png", "img2.png"}


def test_import_dedup_by_sha256_across_batches(
    client: TestClient, tmp_path: Path
) -> None:
    first = tmp_path / "first"
    first.mkdir()
    _write_png(first / "a.png", 7)
    second = tmp_path / "second"
    second.mkdir()
    shutil.copyfile(first / "a.png", second / "a_copy.png")
    _write_png(second / "b.png", 8)

    assert _start_and_wait(client, first)["imported_count"] == 1
    batch = _start_and_wait(client, second)
    assert batch["skipped_count"] == 1
    assert batch["imported_count"] == 1

    with SessionLocal() as session:
        assert len(session.scalars(select(Image)).all()) == 2


def test_import_counts_unreadable_file_as_failed_and_cleans_up(
    client: TestClient, source_dir: Path
) -> None:
    (source_dir / "broken.png").write_bytes(b"definitely not an image")

    batch = _start_and_wait(client, source_dir)
    assert batch["file_count"] == 1
    assert batch["failed_count"] == 1
    assert batch["imported_count"] == 0

    # the copy made before the read failure must not remain in storage
    assert [p for p in (DATA_DIR / "images").rglob("*") if p.is_file()] == []


def test_import_ignores_non_image_extensions(
    client: TestClient, source_dir: Path
) -> None:
    (source_dir / "notes.txt").write_text("x", encoding="utf-8")
    (source_dir / "anim.gif").write_bytes(b"GIF89a")

    batch = _start_and_wait(client, source_dir)
    assert batch["file_count"] == 0
    assert batch["imported_count"] == 0


def test_import_recursive_flag(client: TestClient, source_dir: Path) -> None:
    (source_dir / "nested").mkdir()
    _write_png(source_dir / "top.png", 11)
    _write_png(source_dir / "nested" / "deep.png", 12)

    shallow = _start_and_wait(client, source_dir)
    assert shallow["file_count"] == 1
    assert shallow["imported_count"] == 1

    deep = _start_and_wait(client, source_dir, recursive=True)
    assert deep["file_count"] == 2
    assert deep["imported_count"] == 1
    assert deep["skipped_count"] == 1


def test_import_rejects_non_directory_source(
    client: TestClient, tmp_path: Path
) -> None:
    missing = tmp_path / "missing"
    assert (
        client.post("/api/imports", json={"source_path": str(missing)}).status_code
        == 422
    )

    a_file = tmp_path / "file.txt"
    a_file.write_text("x", encoding="utf-8")
    assert (
        client.post("/api/imports", json={"source_path": str(a_file)}).status_code
        == 422
    )


def test_scan_filters_by_image_extension_and_honors_recursive(tmp_path: Path) -> None:
    from app.services import imports as imports_service

    (tmp_path / "nested").mkdir()
    _write_png(tmp_path / "a.png", 1)
    _write_png(tmp_path / "b_tmp.png", 2)
    (tmp_path / "b_tmp.png").rename(tmp_path / "b.PNG")
    _write_png(tmp_path / "nested" / "c.jpeg", 3)
    (tmp_path / "notes.txt").write_text("x", encoding="utf-8")

    flat = [
        p.relative_to(tmp_path).as_posix()
        for p in imports_service._scan(tmp_path, False)
    ]
    assert flat == ["a.png", "b.PNG"]

    deep = [
        p.relative_to(tmp_path).as_posix()
        for p in imports_service._scan(tmp_path, True)
    ]
    assert deep == ["a.png", "b.PNG", "nested/c.jpeg"]
