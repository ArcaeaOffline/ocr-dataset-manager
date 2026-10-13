from types import SimpleNamespace

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db import SessionLocal
from app.models import B30Component, B30Result
from app.ocr.b30 import LAYOUTS

LAYOUT_ID = next(iter(LAYOUTS))
OTHER_LAYOUT_ID = next(id_ for id_ in LAYOUTS if id_ != LAYOUT_ID)

# same field sets as B30Result in frontend/src/api.ts - the wire contract
COMPONENT_KEYS = {
    "index",
    "song_id",
    "rating_class",
    "score",
    "pure",
    "far",
    "lost",
    "pure_shiny",
    "clear_status",
    "checked",
}
RESULT_KEYS = {"layout", "components", "updated_at"}


def _component(index: int, **overrides: object) -> dict[str, object]:
    fields: dict[str, object] = {
        "index": index,
        "song_id": f"song_{index}",
        "rating_class": index % 5,
        "score": 9_000_000 + index,
        "pure": 900,
        "far": 80,
        "lost": 8,
        "pure_shiny": 12,
        "clear_status": 1,
        "checked": True,
    }
    fields.update(overrides)
    return fields


def test_get_b30_result_without_row_returns_null(
    client: TestClient, seed: SimpleNamespace
) -> None:
    image = seed.image()

    response = client.get(f"/api/images/{image.id}/b30_result")
    assert response.status_code == 200
    assert response.json() is None


def test_put_b30_result_creates_rows_and_echoes(
    client: TestClient, seed: SimpleNamespace
) -> None:
    image = seed.image()
    components = [_component(0), _component(1), _component(2)]

    response = client.put(
        f"/api/images/{image.id}/b30_result",
        json={"layout": LAYOUT_ID, "components": components},
    )
    assert response.status_code == 200
    body = response.json()
    assert set(body) == RESULT_KEYS
    assert body["layout"] == LAYOUT_ID
    # components echo back ordered by grid index
    assert body["components"] == components
    assert all(set(c) == COMPONENT_KEYS for c in body["components"])

    with SessionLocal() as session:
        result = session.get(B30Result, image.id)
        assert result is not None
        assert result.layout == LAYOUT_ID
        rows = session.scalars(
            select(B30Component).where(B30Component.image_id == image.id)
        ).all()
        assert len(rows) == 3


def test_put_b30_result_upserts_only_given_components(
    client: TestClient, seed: SimpleNamespace
) -> None:
    image = seed.image()

    def put(components: list[dict[str, object]]) -> None:
        client.put(
            f"/api/images/{image.id}/b30_result",
            json={"layout": LAYOUT_ID, "components": components},
        )

    put([_component(0), _component(1), _component(2)])
    put([_component(1, score=1)])

    with SessionLocal() as session:
        rows = {
            row.component_index: row
            for row in session.scalars(
                select(B30Component).where(B30Component.image_id == image.id)
            )
        }
    assert set(rows) == {0, 1, 2}
    assert rows[0].score == 9_000_000
    assert rows[1].score == 1
    assert rows[2].score == 9_000_002


def test_put_b30_result_layout_switch_clears_components(
    client: TestClient, seed: SimpleNamespace
) -> None:
    image = seed.image()
    client.put(
        f"/api/images/{image.id}/b30_result",
        json={"layout": LAYOUT_ID, "components": [_component(i) for i in range(3)]},
    )

    response = client.put(
        f"/api/images/{image.id}/b30_result",
        json={"layout": OTHER_LAYOUT_ID, "components": [_component(0)]},
    )
    assert response.status_code == 200

    # stale rows of the old layout would count toward the new one's completion
    with SessionLocal() as session:
        result = session.get(B30Result, image.id)
        assert result is not None
        assert result.layout == OTHER_LAYOUT_ID
        rows = session.scalars(
            select(B30Component).where(B30Component.image_id == image.id)
        ).all()
        assert len(rows) == 1


def test_put_b30_result_same_layout_keeps_components(
    client: TestClient, seed: SimpleNamespace
) -> None:
    image = seed.image()
    for _ in range(2):
        client.put(
            f"/api/images/{image.id}/b30_result",
            json={"layout": LAYOUT_ID, "components": [_component(i) for i in range(3)]},
        )

    with SessionLocal() as session:
        rows = session.scalars(
            select(B30Component).where(B30Component.image_id == image.id)
        ).all()
        assert len(rows) == 3

    response = client.put(
        f"/api/images/{image.id}/b30_result",
        json={"layout": "bogus", "components": []},
    )
    assert response.status_code == 422
