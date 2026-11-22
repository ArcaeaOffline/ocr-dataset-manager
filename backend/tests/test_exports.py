import json
import threading
import time
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError

from app import storage
from app.config import EXPORTS_DIR
from app.db import SessionLocal, init_db
from app.models import Export, Image

# same field set as ExportOut in frontend/src/api.ts - the wire contract
EXPORT_KEYS = {
    "id",
    "name",
    "started_at",
    "finished_at",
    "file_count",
    "exported_count",
    "skipped_count",
    "failed_count",
    "error",
}

FULL_FIELDS = dict(
    score=9123456,
    high_score=9123456,
    high_score_delta=1234,
    pure=100,
    pure_shiny=5,
    far=12,
    lost=3,
    max_recall=456,
    far_late=12,
    pure_late=34,
    far_early=56,
    pure_early=78,
)


def _store_image(seed: SimpleNamespace, *, fill: int = 0) -> Image:
    """A seeded image row backed by a real (synthetic) stored file, so
    the export geometry chain can read it. 1280x720 keeps both T1/T2
    rect sets non-degenerate."""
    image = seed.image()
    path = storage.path_for(image.relative_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    assert cv2.imwrite(str(path), np.full((720, 1280, 3), fill, dtype=np.uint8))
    return image


def _set_hidden(client: TestClient, image_id: str) -> None:
    response = client.put(f"/api/images/{image_id}/hidden", json={"hidden": True})
    assert response.status_code == 200


def _wait_finished(
    client: TestClient, export_id: str, timeout_s: float = 15.0
) -> dict[str, object]:
    """start_export runs the pipeline in a daemon thread. Poll the export
    row until it carries finished_at."""
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        response = client.get(f"/api/exports/{export_id}")
        assert response.status_code == 200
        body = response.json()
        if body["finished_at"] is not None:
            return body
        time.sleep(0.05)
    pytest.fail(f"export {export_id} did not finish within {timeout_s}s")


def _start_and_wait(client: TestClient) -> dict[str, object]:
    response = client.post("/api/exports")
    assert response.status_code == 200
    assert set(response.json()) == EXPORT_KEYS
    return _wait_finished(client, response.json()["id"])


def _export_name(export: dict[str, object]) -> str:
    """The services.exports.export_name rendering of a JSON response."""
    started = datetime.fromisoformat(str(export["started_at"]))
    return f"{started:%Y%m%d_%H%M%S}_{export['id']}"


def _export_dir(export: dict[str, object]) -> Path:
    return EXPORTS_DIR / _export_name(export)


def _manifest(export: dict[str, object]) -> list[dict[str, object]]:
    lines = (
        (_export_dir(export) / "manifest.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    )
    return [json.loads(line) for line in lines]


def _samples_by_field(samples: list[dict[str, object]]) -> dict[str, dict[str, object]]:
    return {str(sample["field"]): sample for sample in samples}


def _meta(export: dict[str, object]) -> dict[str, object]:
    return json.loads((_export_dir(export) / "meta.json").read_text(encoding="utf-8"))


@pytest.fixture
def running_gate(monkeypatch: pytest.MonkeyPatch) -> Iterator[threading.Event]:
    """Replace the export thread body with a gate the test controls, so
    running-state assertions are deterministic."""
    gate = threading.Event()

    def gated_run(export_id: str) -> None:
        gate.wait(10)
        with SessionLocal() as session:
            export = session.get(Export, export_id)
            if export is not None:
                export.finished_at = datetime.now(UTC)
                session.commit()

    monkeypatch.setattr("app.services.exports._run", gated_run)
    yield gate
    gate.set()


def test_export_lifecycle_and_manifest(
    client: TestClient, seed: SimpleNamespace
) -> None:
    image = _store_image(seed)
    seed.device_result(image, checked=True, rois_type=0, **FULL_FIELDS)

    export = _start_and_wait(client)
    assert export["name"] == _export_name(export)
    assert export["file_count"] == 1
    assert export["exported_count"] == 1
    assert export["skipped_count"] == 0
    assert export["failed_count"] == 0
    assert export["error"] is None
    assert any(e["id"] == export["id"] for e in client.get("/api/exports").json())

    export_dir = _export_dir(export)
    samples = _manifest(export)
    assert {s["field"] for s in samples} == {
        "score",
        "high_score",
        "high_score_delta",
        "pure",
        "pure_shiny",
        "far",
        "lost",
        "max_recall",
        "early_late",
    }
    for sample in samples:
        assert sample["rois_type"] == 0
        assert sample["source_image_id"] == image.id
        assert (export_dir / str(sample["image"])).is_file()

    meta = _meta(export)
    assert meta["file_count"] == 1
    assert meta["exported_count"] == 1
    assert meta["skip_reasons"] == {}
    meta_per_field = meta["per_field"]
    assert isinstance(meta_per_field, dict)
    assert set(meta_per_field) == {s["field"] for s in samples}
    assert meta["per_rois_type"] == {"0": 9}
    assert (export_dir / "dataset.py").is_file()
    assert (EXPORTS_DIR / f"{_export_name(export)}.zip").is_file()
    # the README carries the orientation the UI does not: loader usage
    # and the counts
    readme = (export_dir / "README.md").read_text(encoding="utf-8")
    assert "RoiTextDataset" in readme
    assert "裁剪图共 9 张" in readme
    assert "导出 1 / 跳过 0 / 失败 0" in readme


def test_export_text_matches_annotate_preview(
    client: TestClient, seed: SimpleNamespace
) -> None:
    image = _store_image(seed)
    seed.device_result(
        image,
        checked=True,
        rois_type=1,
        score=9123456,
        high_score=0,
        high_score_delta=-1234,
        pure=100,
        pure_shiny=5,
        far=12,
        lost=3,
        max_recall=456,
        far_late=12,
        pure_late=34,
        far_early=56,
        pure_early=78,
    )

    export = _start_and_wait(client)
    samples = _samples_by_field(_manifest(export))
    assert samples["score"]["text"] == "09'123'456"
    assert samples["score"]["value"] == 9123456
    # a zero high score renders unpadded
    assert samples["high_score"]["text"] == "0"
    assert samples["high_score"]["value"] == 0
    assert samples["high_score_delta"]["text"] == "-00'001'234"
    assert samples["pure"]["text"] == "100"
    assert samples["early_late"]["text"] == "L12(P34) E56(P78)"
    assert samples["early_late"]["value"] is None
    assert samples["early_late"]["values"] == {
        "far_late": 12,
        "pure_late": 34,
        "far_early": 56,
        "pure_early": 78,
    }


def test_export_early_late_drops_incomplete_pure_info(
    client: TestClient, seed: SimpleNamespace
) -> None:
    """Incomplete PURE early/late data cannot occur on a real screenshot.
    When stored annotations carry it anyway, the whole PURE info drops:
    text renders "L… E…" and the values carry no pure parts."""
    image = _store_image(seed)
    seed.device_result(
        image,
        checked=True,
        rois_type=0,
        far_late=12,
        pure_late=34,
        far_early=56,
        pure_early=None,
    )

    samples = _samples_by_field(_manifest(_start_and_wait(client)))
    early_late = samples["early_late"]
    assert early_late["text"] == "L12 E56"
    assert early_late["values"] == {"far_late": 12, "far_early": 56}


def test_export_scope_checked_visible_only(
    client: TestClient, seed: SimpleNamespace
) -> None:
    exported = _store_image(seed)
    seed.device_result(exported, checked=True, rois_type=0, score=1, pure=2)

    no_rois_type = _store_image(seed)
    seed.device_result(no_rois_type, checked=True, score=1)

    unchecked = _store_image(seed)
    seed.device_result(unchecked, rois_type=0, score=1)

    hidden = _store_image(seed)
    seed.device_result(hidden, checked=True, rois_type=0, score=1)
    _set_hidden(client, hidden.id)

    export = _start_and_wait(client)
    # unchecked and hidden images are not part of the job at all; the
    # missing rois_type is a counted skip
    assert export["file_count"] == 2
    assert export["exported_count"] == 1
    assert export["skipped_count"] == 1
    assert export["failed_count"] == 0

    samples = _manifest(export)
    assert {s["source_image_id"] for s in samples} == {exported.id}
    assert _meta(export)["skip_reasons"] == {"rois_type_missing": 1}


def test_export_skips_missing_storage_file(
    client: TestClient, seed: SimpleNamespace
) -> None:
    image = seed.image()
    seed.device_result(image, checked=True, rois_type=0, score=1)

    export = _start_and_wait(client)
    assert export["skipped_count"] == 1
    assert export["exported_count"] == 0
    assert _meta(export)["skip_reasons"] == {"file_unreadable": 1}


def test_export_empty_dataset(client: TestClient) -> None:
    export = _start_and_wait(client)
    assert export["file_count"] == 0
    assert export["exported_count"] == 0

    manifest = (_export_dir(export) / "manifest.jsonl").read_text(encoding="utf-8")
    assert manifest == ""
    assert (EXPORTS_DIR / f"{_export_name(export)}.zip").is_file()
    # the empty branch of the README statistics
    readme = (_export_dir(export) / "README.md").read_text(encoding="utf-8")
    assert "裁剪图共 0 张" in readme


def test_export_crops_match_annotate_view(
    client: TestClient, seed: SimpleNamespace
) -> None:
    """The exported crops must be pixel-identical to what the annotate
    view displays: the device_rois rects applied to the cropped canvas."""
    from arcaea_offline_ocr.crop import CropBlackEdges, crop_xywh

    from app.services import prefill

    image = _store_image(seed, fill=40)
    seed.device_result(image, checked=True, rois_type=1, **FULL_FIELDS)

    export = _start_and_wait(client)
    samples = _manifest(export)
    assert samples
    export_dir = _export_dir(export)
    stored = cv2.imread(str(storage.path_for(image.relative_path)))
    assert stored is not None
    canvas = CropBlackEdges.crop_or_original(stored)
    rects = prefill.device_rois(image.relative_path, 1)["rects"]
    for sample in samples:
        x, y, w, h = rects[str(sample["field"])]
        expected = crop_xywh(canvas, (x, y, w, h))
        exported = cv2.imread(str(export_dir / str(sample["image"])))
        assert exported is not None
        assert np.array_equal(exported, expected)


def test_export_rejects_concurrent_start(
    client: TestClient, running_gate: threading.Event
) -> None:
    response = client.post("/api/exports")
    assert response.status_code == 200
    assert client.post("/api/exports").status_code == 409

    running_gate.set()
    _wait_finished(client, response.json()["id"])
    assert client.post("/api/exports").status_code == 200


def test_db_rejects_second_running_export_row() -> None:
    """uq_exports_single_running is the real single-run guard;
    start_export's select is only the fast path."""
    # runs without the client fixture, which is what otherwise migrates
    # the tmp database
    init_db()
    with SessionLocal() as session:
        session.add(Export())
        session.commit()
        session.add(Export())
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()
        # finished rows leave the partial index, so they stay unconstrained
        session.execute(update(Export).values(finished_at=datetime.now(UTC)))
        session.add(Export())
        session.commit()


def test_download_and_delete_lifecycle(
    client: TestClient, seed: SimpleNamespace, running_gate: threading.Event
) -> None:
    image = _store_image(seed)
    seed.device_result(image, checked=True, rois_type=0, score=1)
    created = client.post("/api/exports").json()
    export_id = str(created["id"])

    # still running: no download, no delete
    assert client.get(f"/api/exports/{export_id}/download").status_code == 409
    assert client.delete(f"/api/exports/{export_id}").status_code == 409
    running_gate.set()
    export = _wait_finished(client, export_id)

    # the gated stub does not produce real artifacts; the download
    # endpoint's contract is row-finished + archive on disk
    export_dir = _export_dir(export)
    export_dir.mkdir(parents=True)
    (export_dir / "manifest.jsonl").write_text("", encoding="utf-8")
    (EXPORTS_DIR / f"{_export_name(export)}.zip").write_bytes(b"PK")

    download = client.get(f"/api/exports/{export_id}/download")
    assert download.status_code == 200
    assert download.headers["content-type"].startswith("application/zip")
    # the archive carries the timestamp-prefixed name, not the bare id
    assert _export_name(export) in download.headers["content-disposition"]

    assert client.delete(f"/api/exports/{export_id}").status_code == 204
    assert not export_dir.exists()
    assert not (EXPORTS_DIR / f"{_export_name(export)}.zip").exists()
    assert client.get(f"/api/exports/{export_id}").status_code == 404
    assert client.delete(f"/api/exports/{export_id}").status_code == 404
    assert client.get(f"/api/exports/{export_id}/download").status_code == 404


def test_job_level_failure_sets_error_not_eternal_running(
    client: TestClient, seed: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A job-level failure must close the job out with an error message
    instead of leaving an eternally running row."""
    image = _store_image(seed)
    seed.device_result(image, checked=True, rois_type=0, score=1)

    def fail(*args: object) -> None:
        raise RuntimeError(f"boom ({args})")

    monkeypatch.setattr("app.services.exports._write_meta", fail)
    export = _start_and_wait(client)
    assert str(export["error"]).startswith("RuntimeError: boom")
    # per-image work completed before the failure
    assert export["exported_count"] == 1
