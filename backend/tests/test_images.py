from datetime import datetime
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.ocr.b30 import LAYOUTS

LAYOUT_ID = next(iter(LAYOUTS))
LAYOUT = LAYOUTS[LAYOUT_ID]


def _set_hidden(
    client: TestClient, image_id: str, hidden: bool = True
) -> dict[str, object]:
    response = client.put(f"/api/images/{image_id}/hidden", json={"hidden": hidden})
    assert response.status_code == 200
    return response.json()

# same field set as ImageItem in frontend/src/api.ts - the wire contract
IMAGE_ITEM_KEYS = {
    "id",
    "relative_path",
    "original_filename",
    "width",
    "height",
    "kind",
    "checked",
    "b30_checked_count",
    "b30_component_count",
    "hidden",
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

    # total counts the same set the items filter, keeping pagination consistent
    assert client.get("/api/images", params={"kind": "b30"}).json()["total"] == 1
    assert client.get("/api/images", params={"kind": "device"}).json()["total"] == 1
    assert (
        client.get("/api/images", params={"kind": "unclassified"}).json()["total"] == 1
    )
    filtered = client.get("/api/images", params={"kind": "b30"}).json()
    assert {i["id"] for i in filtered["items"]} == {b30.id}
    device_items = client.get("/api/images", params={"kind": "device"}).json()["items"]
    assert {i["id"] for i in device_items} == {device.id}
    unclassified = client.get(
        "/api/images", params={"kind": "unclassified"}
    ).json()["items"]
    assert {i["id"] for i in unclassified} == {bare.id}


def test_total_follows_unchecked_filter(
    client: TestClient, seed: SimpleNamespace
) -> None:
    checked = seed.image()
    seed.device_result(checked, checked=True)
    seed.image()

    response = client.get("/api/images", params={"unchecked_only": True}).json()
    assert response["total"] == 1


def test_unchecked_only_spans_both_queues(
    client: TestClient, seed: SimpleNamespace
) -> None:
    checked = seed.image()
    seed.device_result(checked, checked=True)
    draft = seed.image()
    seed.device_result(draft, checked=False)
    bare = seed.image()
    b30_no_layout = seed.image()
    seed.b30_result(b30_no_layout, layout=None)

    items = client.get("/api/images", params={"unchecked_only": True}).json()
    # not-fully-checked b30 images belong to the unchecked view too
    assert items["total"] == 3
    assert {i["id"] for i in items["items"]} == {draft.id, bare.id, b30_no_layout.id}


def test_unchecked_only_all_includes_partial_b30(
    client: TestClient, seed: SimpleNamespace
) -> None:
    device_done = seed.image()
    seed.device_result(device_done, checked=True)
    bare = seed.image()

    full = seed.image()
    seed.b30_result(full, layout=LAYOUT_ID)
    for idx in range(LAYOUT.component_count):
        seed.b30_component(full, idx, checked=True)

    partial = seed.image()
    seed.b30_result(partial, layout=LAYOUT_ID)
    seed.b30_component(partial, 0, checked=True)

    items = client.get("/api/images", params={"unchecked_only": True}).json()
    assert items["total"] == 2
    assert {i["id"] for i in items["items"]} == {bare.id, partial.id}


def test_unchecked_only_excludes_hybrid_with_checked_device_row(
    client: TestClient, seed: SimpleNamespace
) -> None:
    """A hybrid image presents as device (queues.kind_of): queue
    membership follows the device checked flag, not the incomplete b30
    row."""
    hybrid = seed.image()
    seed.device_result(hybrid, checked=True)
    seed.b30_result(hybrid, layout=LAYOUT_ID)
    seed.b30_component(hybrid, 0, checked=True)

    all_view = client.get("/api/images", params={"unchecked_only": True}).json()
    assert all_view["items"] == []
    b30_view = client.get(
        "/api/images", params={"unchecked_only": True, "kind": "b30"}
    ).json()
    assert b30_view["items"] == []


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
    assert by_id[full.id]["b30_checked_count"] == LAYOUT.component_count
    assert by_id[full.id]["b30_component_count"] == LAYOUT.component_count
    assert by_id[partial.id]["checked"] is False
    assert by_id[partial.id]["b30_checked_count"] == 1
    assert by_id[partial.id]["b30_component_count"] == LAYOUT.component_count
    assert by_id[no_layout.id]["checked"] is False
    assert by_id[no_layout.id]["b30_checked_count"] == 0
    assert by_id[no_layout.id]["b30_component_count"] is None
    assert by_id[device.id]["kind"] == "device"
    assert by_id[device.id]["checked"] is True
    assert by_id[device.id]["b30_checked_count"] is None
    assert by_id[device.id]["b30_component_count"] is None
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
        (full.id, "b30", True, LAYOUT.component_count),
        (partial.id, "b30", False, 1),
        (device.id, "device", True, None),
        (bare.id, "unclassified", None, None),
    ]
    for image_id, kind, checked, b30_checked in cases:
        body = client.get(f"/api/images/{image_id}").json()
        assert (body["kind"], body["checked"]) == (kind, checked)
        assert body["b30_checked_count"] == b30_checked
        assert set(body) == IMAGE_ITEM_KEYS


def test_image_detail_hybrid_prefers_device_row(
    client: TestClient, seed: SimpleNamespace
) -> None:
    """list and detail agree with kind_of on hybrids: the checked flag
    comes from the device row."""
    hybrid = seed.image()
    seed.device_result(hybrid, checked=False)
    seed.b30_result(hybrid, layout=LAYOUT_ID)
    seed.b30_component(hybrid, 0, checked=True)

    listed = client.get("/api/images", params={"kind": "device"}).json()
    assert listed["total"] == 1
    assert listed["items"][0]["checked"] is False
    assert listed["items"][0]["b30_checked_count"] is None
    detail = client.get(f"/api/images/{hybrid.id}").json()
    assert detail["kind"] == "device"
    assert detail["checked"] is False
    assert detail["b30_checked_count"] is None


def test_image_detail_404(client: TestClient) -> None:
    assert client.get("/api/images/missing-id").status_code == 404


def test_hidden_default_excluded_and_only_listed(
    client: TestClient, seed: SimpleNamespace
) -> None:
    hidden_img = seed.image()
    seed.device_result(hidden_img, checked=True)
    visible = seed.image()

    body = _set_hidden(client, hidden_img.id)
    assert body["hidden"] is True

    default = client.get("/api/images").json()
    assert default["total"] == 1
    assert {i["id"] for i in default["items"]} == {visible.id}

    only = client.get("/api/images", params={"hidden": "only"}).json()
    assert only["total"] == 1
    assert {i["id"] for i in only["items"]} == {hidden_img.id}


def test_hidden_put_idempotent_and_reversible(
    client: TestClient, seed: SimpleNamespace
) -> None:
    image = seed.image()

    for _ in range(2):
        body = _set_hidden(client, image.id)
        assert body["hidden"] is True
        assert set(body) == IMAGE_ITEM_KEYS
    assert client.get(f"/api/images/{image.id}").json()["hidden"] is True

    assert _set_hidden(client, image.id, hidden=False)["hidden"] is False
    assert client.get(f"/api/images/{image.id}").json()["hidden"] is False
    assert client.get("/api/images").json()["total"] == 1


def test_hidden_excluded_from_kind_and_unchecked_views(
    client: TestClient, seed: SimpleNamespace
) -> None:
    hidden_bare = seed.image()
    hidden_device = seed.image()
    seed.device_result(hidden_device, checked=False)
    visible = seed.image()
    for image in (hidden_bare, hidden_device):
        _set_hidden(client, image.id)

    unchecked = client.get("/api/images", params={"unchecked_only": True}).json()
    assert {i["id"] for i in unchecked["items"]} == {visible.id}
    assert unchecked["total"] == 1
    expected_by_kind = {
        "device": set(),
        "b30": set(),
        "unclassified": {visible.id},
    }
    for kind, expected in expected_by_kind.items():
        view = client.get("/api/images", params={"kind": kind}).json()
        assert {i["id"] for i in view["items"]} == expected
        assert view["total"] == len(expected)


def test_hidden_validates_params_and_missing_image(client: TestClient) -> None:
    assert (
        client.put("/api/images/missing-id/hidden", json={"hidden": True}).status_code
        == 404
    )
    assert (
        client.get("/api/images", params={"hidden": "bogus"}).status_code == 422
    )
