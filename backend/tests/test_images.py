from datetime import datetime
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.ocr.b30 import LAYOUTS

LAYOUT_ID = next(iter(LAYOUTS))
LAYOUT = LAYOUTS[LAYOUT_ID]

# same field set as ImageItem in frontend/src/api.ts - the wire contract
IMAGE_ITEM_KEYS = {
    "id",
    "relative_path",
    "original_filename",
    "width",
    "height",
    "kind",
    "checked",
    "created_at",
}


def test_kind_filter_and_total(client: TestClient, seed: SimpleNamespace) -> None:
    device = seed.image()
    seed.device_result(device, checked=True)
    b30 = seed.image()
    seed.b30_result(b30, layout=LAYOUT_ID)
    bare = seed.image()

    listing = client.get("/api/images").json()
    assert listing["total"] == 3
    assert {i["id"] for i in listing["items"]} == {device.id, b30.id, bare.id}
    assert all(set(item) == IMAGE_ITEM_KEYS for item in listing["items"])

    # total counts all images regardless of the kind filter
    filtered = client.get("/api/images", params={"kind": "b30"}).json()
    assert filtered["total"] == 3
    assert {i["id"] for i in filtered["items"]} == {b30.id}
    device_items = client.get("/api/images", params={"kind": "device"}).json()["items"]
    assert {i["id"] for i in device_items} == {device.id}
    unclassified = client.get(
        "/api/images", params={"kind": "unclassified"}
    ).json()["items"]
    assert {i["id"] for i in unclassified} == {bare.id}


def test_unchecked_only_device_queue(
    client: TestClient, seed: SimpleNamespace
) -> None:
    checked = seed.image()
    seed.device_result(checked, checked=True)
    draft = seed.image()
    seed.device_result(draft, checked=False)
    bare = seed.image()
    b30_only = seed.image()
    seed.b30_result(b30_only, layout=None)

    items = client.get("/api/images", params={"unchecked_only": True}).json()["items"]
    # a draft counts as unchecked; b30-classified images belong to the b30 queue
    assert {i["id"] for i in items} == {draft.id, bare.id}


def test_unchecked_only_b30_queue(client: TestClient, seed: SimpleNamespace) -> None:
    done = seed.image()
    seed.b30_result(done, layout=LAYOUT_ID)
    for idx in range(LAYOUT.component_count):
        seed.b30_component(done, idx, checked=True)

    partial = seed.image()
    seed.b30_result(partial, layout=LAYOUT_ID)
    for idx in range(LAYOUT.component_count - 1):
        seed.b30_component(partial, idx, checked=True)

    no_layout = seed.image()
    seed.b30_result(no_layout, layout=None)

    items = client.get(
        "/api/images", params={"unchecked_only": True, "kind": "b30"}
    ).json()["items"]
    # an unknown layout can never count as done
    assert {i["id"] for i in items} == {partial.id, no_layout.id}


def test_checked_and_kind_derivation_in_list(
    client: TestClient, seed: SimpleNamespace
) -> None:
    full = seed.image()
    seed.b30_result(full, layout=LAYOUT_ID)
    for idx in range(LAYOUT.component_count):
        seed.b30_component(full, idx, checked=True)

    partial = seed.image()
    seed.b30_result(partial, layout=LAYOUT_ID)
    seed.b30_component(partial, 0, checked=True)

    no_layout = seed.image()
    seed.b30_result(no_layout, layout=None)

    device = seed.image()
    seed.device_result(device, checked=True)
    bare = seed.image()

    by_id = {i["id"]: i for i in client.get("/api/images").json()["items"]}
    assert by_id[full.id]["kind"] == "b30"
    assert by_id[full.id]["checked"] is True
    assert by_id[partial.id]["checked"] is False
    assert by_id[no_layout.id]["checked"] is False
    assert by_id[device.id]["kind"] == "device"
    assert by_id[device.id]["checked"] is True
    assert by_id[bare.id]["kind"] == "unclassified"
    assert by_id[bare.id]["checked"] is None


def test_list_pagination_and_ordering(
    client: TestClient, seed: SimpleNamespace
) -> None:
    old = seed.image(created_at=datetime(2026, 1, 1))
    mid = seed.image(created_at=datetime(2026, 1, 2))
    new = seed.image(created_at=datetime(2026, 1, 3))

    assert [i["id"] for i in client.get("/api/images").json()["items"]] == [
        new.id,
        mid.id,
        old.id,
    ]
    page = client.get("/api/images", params={"offset": 1, "limit": 1}).json()
    assert [i["id"] for i in page["items"]] == [mid.id]


def test_list_limit_capped_at_200(client: TestClient, seed: SimpleNamespace) -> None:
    for _ in range(201):
        seed.image()

    page = client.get("/api/images", params={"limit": 500}).json()
    assert page["total"] == 201
    assert len(page["items"]) == 200


def test_list_rejects_unknown_kind(client: TestClient) -> None:
    response = client.get("/api/images", params={"kind": "bogus"})
    assert response.status_code == 422


def test_image_detail_derives_kind_and_checked(
    client: TestClient, seed: SimpleNamespace
) -> None:
    full = seed.image()
    seed.b30_result(full, layout=LAYOUT_ID)
    for idx in range(LAYOUT.component_count):
        seed.b30_component(full, idx, checked=True)

    partial = seed.image()
    seed.b30_result(partial, layout=LAYOUT_ID)
    seed.b30_component(partial, 0, checked=True)

    device = seed.image()
    seed.device_result(device, checked=True)
    bare = seed.image()

    cases = [
        (full.id, "b30", True),
        (partial.id, "b30", False),
        (device.id, "device", True),
        (bare.id, "unclassified", None),
    ]
    for image_id, kind, checked in cases:
        body = client.get(f"/api/images/{image_id}").json()
        assert (body["kind"], body["checked"]) == (kind, checked)
        assert set(body) == IMAGE_ITEM_KEYS


def test_image_detail_404(client: TestClient) -> None:
    assert client.get("/api/images/missing-id").status_code == 404
