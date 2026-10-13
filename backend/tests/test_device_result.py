from types import SimpleNamespace

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db import SessionLocal
from app.models import DeviceResult
from app.routers.images import DeviceResultIn

# same field set as DeviceResult in frontend/src/api.ts - the wire contract
RESULT_KEYS = set(DeviceResultIn.model_fields) | {"image_id", "updated_at"}


def _fields(**overrides: object) -> dict[str, object]:
    fields: dict[str, object] = {
        "rois_type": 1,
        "song_id": "song_a",
        "partner_id": "1",
        "rating_class": 2,
        "clear_status": 3,
        "score": 10_000_000,
        "pure": 9000,
        "far": 800,
        "lost": 100,
        "max_recall": 9900,
        "high_score": 9_800_000,
        "high_score_delta": 1200,
        "pure_shiny": 1234,
        "pure_early": 5,
        "pure_late": 6,
        "far_early": 7,
        "far_late": 8,
        "checked": True,
    }
    fields.update(overrides)
    return fields


def test_get_result_without_row_returns_null(
    client: TestClient, seed: SimpleNamespace
) -> None:
    image = seed.image()

    response = client.get(f"/api/images/{image.id}/result")
    assert response.status_code == 200
    assert response.json() is None


def test_put_result_creates_row_and_echoes(
    client: TestClient, seed: SimpleNamespace
) -> None:
    image = seed.image()

    response = client.put(f"/api/images/{image.id}/result", json=_fields())
    assert response.status_code == 200
    body = response.json()
    assert set(body) == RESULT_KEYS
    assert body["image_id"] == image.id
    assert body["updated_at"].endswith("Z")
    for key, value in _fields().items():
        assert body[key] == value

    assert client.get(f"/api/images/{image.id}/result").json() == body


def test_put_result_updates_existing_row(
    client: TestClient, seed: SimpleNamespace
) -> None:
    image = seed.image()
    client.put(f"/api/images/{image.id}/result", json=_fields())

    response = client.put(
        f"/api/images/{image.id}/result", json=_fields(score=1, checked=False)
    )
    assert response.status_code == 200

    with SessionLocal() as session:
        rows = session.scalars(select(DeviceResult)).all()
        assert len(rows) == 1
        assert rows[0].score == 1
        assert rows[0].checked is False
