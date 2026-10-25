from dataclasses import dataclass
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.ocr.b30 import LAYOUTS
from app.services import prefill

LAYOUT_ID = next(iter(LAYOUTS))

DEVICE_PREFILL: dict[str, object] = {
    "rois_type": 1,
    "score": 10_000_000,
    "song_id": "song_a",
}

IMMUTABLE_CACHE = "public, max-age=31536000, immutable"


def _install(monkeypatch: pytest.MonkeyPatch, **fns: object) -> None:
    for name, fn in fns.items():
        monkeypatch.setattr(prefill, name, fn)


def test_prefill_prefers_probed_b30_layout(
    client: TestClient, seed: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    image = seed.image()
    device_calls: list[str] = []

    def _get(image_id: str, _relative_path: str) -> dict[str, object]:
        device_calls.append(image_id)
        return DEVICE_PREFILL

    _install(monkeypatch, get=_get, b30_layout=lambda *_: LAYOUT_ID)

    body = client.get(f"/api/images/{image.id}/prefill").json()
    assert body == {"kind": "b30", "layout": LAYOUT_ID}
    assert device_calls == []


def test_prefill_falls_back_to_device_proposal(
    client: TestClient, seed: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    image = seed.image()
    _install(
        monkeypatch, b30_layout=lambda *_: None, get=lambda *_: dict(DEVICE_PREFILL)
    )

    body = client.get(f"/api/images/{image.id}/prefill").json()
    assert body == {"kind": "device", "prefill": DEVICE_PREFILL}


def test_prefill_flow_device_forces_device_proposal(
    client: TestClient, seed: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    image = seed.image()
    probe_calls: list[str] = []

    def _layout(image_id: str, _relative_path: str) -> str:
        probe_calls.append(image_id)
        return LAYOUT_ID

    _install(monkeypatch, b30_layout=_layout, get=lambda *_: dict(DEVICE_PREFILL))

    body = client.get(
        f"/api/images/{image.id}/prefill", params={"flow": "device"}
    ).json()
    assert body == {"kind": "device", "prefill": DEVICE_PREFILL}
    assert probe_calls == []


def test_prefill_rejects_unknown_flow(
    client: TestClient, seed: SimpleNamespace
) -> None:
    image = seed.image()

    response = client.get(f"/api/images/{image.id}/prefill", params={"flow": "bogus"})
    assert response.status_code == 422


def test_prefill_maps_service_value_error_to_422(
    client: TestClient, seed: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    image = seed.image()

    def _boom(*_: object) -> dict[str, object]:
        raise ValueError("stored file unreadable")

    _install(monkeypatch, b30_layout=lambda *_: None, get=_boom)

    response = client.get(f"/api/images/{image.id}/prefill", params={"flow": "device"})
    assert response.status_code == 422


def test_b30_component_prefill_serializes_dataclass(
    client: TestClient, seed: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    @dataclass
    class FakeComponent:
        index: int
        song_id: str | None = None

    seen: dict[str, object] = {}

    def _component(
        _image_id: str, _relative_path: str, index: int, layout: str | None = None
    ) -> FakeComponent:
        seen["layout"] = layout
        return FakeComponent(index=index, song_id="song_a")

    image = seed.image()
    _install(monkeypatch, b30_component=_component)

    body = client.get(f"/api/images/{image.id}/b30_prefill/3").json()
    assert body == {"index": 3, "song_id": "song_a"}
    assert seen["layout"] is None

    client.get(f"/api/images/{image.id}/b30_prefill/3", params={"layout": LAYOUT_ID})
    assert seen["layout"] == LAYOUT_ID
    # unknown layouts are rejected before reaching the service
    response = client.get(
        f"/api/images/{image.id}/b30_prefill/3", params={"layout": "bogus"}
    )
    assert response.status_code == 422


def test_b30_component_prefill_422_when_not_b30(
    client: TestClient, seed: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    image = seed.image()
    _install(monkeypatch, b30_component=lambda *_: None)

    response = client.get(f"/api/images/{image.id}/b30_prefill/0")
    assert response.status_code == 422


def test_b30_card_serves_jpeg_with_immutable_cache(
    client: TestClient, seed: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    image = seed.image()
    _install(monkeypatch, b30_card_jpeg=lambda *_: b"jpeg-bytes")

    response = client.get(f"/api/images/{image.id}/b30_card/0")
    assert response.status_code == 200
    assert response.content == b"jpeg-bytes"
    assert response.headers["content-type"] == "image/jpeg"
    assert response.headers["cache-control"] == IMMUTABLE_CACHE


def test_b30_card_error_paths(
    client: TestClient, seed: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    image = seed.image()

    _install(monkeypatch, b30_card_jpeg=lambda *_: None)
    assert client.get(f"/api/images/{image.id}/b30_card/0").status_code == 422

    def _boom(*_: object) -> bytes:
        raise ValueError("failed to encode card image")

    _install(monkeypatch, b30_card_jpeg=_boom)
    assert client.get(f"/api/images/{image.id}/b30_card/0").status_code == 422

    _install(monkeypatch, b30_card_jpeg=lambda *_: b"jpeg-bytes")
    response = client.get(
        f"/api/images/{image.id}/b30_card/0", params={"layout": "bogus"}
    )
    assert response.status_code == 422
