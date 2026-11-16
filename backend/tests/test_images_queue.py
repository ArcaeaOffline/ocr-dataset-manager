from collections.abc import Callable
from datetime import datetime, timedelta
from types import SimpleNamespace
from typing import TypeAlias

import pytest
from fastapi.testclient import TestClient

from app.ocr.b30 import LAYOUTS
from app.services import prefill

LAYOUT_ID = next(iter(LAYOUTS))
LAYOUT = LAYOUTS[LAYOUT_ID]

_BASE = datetime(2026, 1, 1)

ProbeLayout: TypeAlias = Callable[
    [str | None | Callable[[str, str], str | None]], list[str]
]


def _t(minutes: int) -> datetime:
    return _BASE + timedelta(minutes=minutes)


def _set_hidden(client: TestClient, image_id: str) -> None:
    response = client.put(f"/api/images/{image_id}/hidden", json={"hidden": True})
    assert response.status_code == 200


@pytest.fixture
def probe_layout(monkeypatch: pytest.MonkeyPatch):
    """Swap prefill.b30_layout for a recording fake. Call with a layout
    id, None, or a callable answering per image id. Returns the call log."""
    calls: list[str] = []

    def _install(
        answer: str | None | Callable[[str, str], str | None],
    ) -> list[str]:
        def _fake(image_id: str, relative_path: str) -> str | None:
            calls.append(image_id)
            if callable(answer):
                return answer(image_id, relative_path)
            return answer

        monkeypatch.setattr(prefill, "b30_layout", _fake)
        return calls

    return _install


def test_next_device_orders_skips_and_wraps(
    client: TestClient, seed: SimpleNamespace
) -> None:
    done = seed.image(created_at=_t(4))
    seed.device_result(done, checked=True)
    b30 = seed.image(created_at=_t(3))
    seed.b30_result(b30, layout=LAYOUT_ID)
    draft = seed.image(created_at=_t(2))
    seed.device_result(draft, checked=False)
    bare = seed.image(created_at=_t(1))

    assert client.get(f"/api/images/{done.id}/next").json() == {"id": draft.id}
    assert client.get(f"/api/images/{draft.id}/next").json() == {"id": bare.id}
    # past the tail of the queue the scan wraps back to its head
    assert client.get(f"/api/images/{bare.id}/next").json() == {"id": draft.id}


def _partial_b30(seed: SimpleNamespace, *, minute: int, filename: str | None):
    image = seed.image(created_at=_t(minute))
    if filename is not None:
        seed.original_filename(image, filename)
    seed.b30_result(image, layout=LAYOUT_ID)
    for idx in range(LAYOUT.component_count - 1):
        seed.b30_component(image, idx, checked=True)
    return image


def test_next_b30_follows_filename_order(
    client: TestClient, seed: SimpleNamespace
) -> None:
    c = _partial_b30(seed, minute=1, filename="c.png")
    b = _partial_b30(seed, minute=2, filename="b.png")
    a = _partial_b30(seed, minute=3, filename="a.png")
    unnamed = _partial_b30(seed, minute=4, filename=None)

    params = {"flow": "b30", "order_by": "original_filename"}
    # descending filenames with NULLs last, wrapping around the cycle
    assert client.get(f"/api/images/{c.id}/next", params=params).json() == {"id": b.id}
    assert client.get(f"/api/images/{b.id}/next", params=params).json() == {"id": a.id}
    assert client.get(f"/api/images/{a.id}/next", params=params).json() == {
        "id": unnamed.id
    }
    # the NULL-keyed tail wraps back to the queue head
    assert client.get(f"/api/images/{unnamed.id}/next", params=params).json() == {
        "id": c.id
    }


def test_prev_b30_walks_backwards_and_wraps(
    client: TestClient, seed: SimpleNamespace
) -> None:
    oldest = _partial_b30(seed, minute=1, filename=None)
    mid = _partial_b30(seed, minute=2, filename=None)
    newest = _partial_b30(seed, minute=3, filename=None)

    params = {"flow": "b30"}
    # prev flips the walk direction: backward from the middle lands on
    # the newer neighbor
    assert client.get(f"/api/images/{mid.id}/prev", params=params).json() == {
        "id": newest.id
    }
    assert client.get(f"/api/images/{oldest.id}/prev", params=params).json() == {
        "id": mid.id
    }
    # backward from the queue head wraps to the queue tail
    assert client.get(f"/api/images/{newest.id}/prev", params=params).json() == {
        "id": oldest.id
    }
    # forward from the tail wraps to the queue head on the same cycle
    assert client.get(f"/api/images/{oldest.id}/next", params=params).json() == {
        "id": newest.id
    }


def test_prev_device_walks_the_same_cycle_backwards(
    client: TestClient, seed: SimpleNamespace
) -> None:
    done = seed.image(created_at=_t(4))
    seed.device_result(done, checked=True)
    b30 = seed.image(created_at=_t(3))
    seed.b30_result(b30, layout=LAYOUT_ID)
    draft = seed.image(created_at=_t(2))
    seed.device_result(draft, checked=False)
    bare = seed.image(created_at=_t(1))

    # backward from the queue head wraps to the queue tail
    assert client.get(f"/api/images/{draft.id}/prev").json() == {"id": bare.id}
    assert client.get(f"/api/images/{bare.id}/prev").json() == {"id": draft.id}
    # a checked image can still anchor the walk
    assert client.get(f"/api/images/{done.id}/prev").json() == {"id": bare.id}


def test_next_device_category_all_and_checked(
    client: TestClient, seed: SimpleNamespace
) -> None:
    done = seed.image(created_at=_t(4))
    seed.device_result(done, checked=True)
    draft = seed.image(created_at=_t(3))
    seed.device_result(draft, checked=False)
    bare = seed.image(created_at=_t(2))
    b30 = seed.image(created_at=_t(1))
    seed.b30_result(b30, layout=LAYOUT_ID)

    # the all category walks device-classified and unclassified images
    # alike (both are annotated in the device flow). B30 rows stay out
    assert client.get(
        f"/api/images/{done.id}/next", params={"category": "all"}
    ).json() == {"id": draft.id}
    assert client.get(
        f"/api/images/{draft.id}/next", params={"category": "all"}
    ).json() == {"id": bare.id}
    assert client.get(
        f"/api/images/{bare.id}/next", params={"category": "all"}
    ).json() == {"id": done.id}
    # the checked queue holds the annotated image alone, so the wrap
    # lands back on it
    assert client.get(
        f"/api/images/{done.id}/next", params={"category": "checked"}
    ).json() == {"id": done.id}
    # with no params the endpoint walks its defaults (flow=device,
    # category=unchecked)
    assert client.get(f"/api/images/{done.id}/next").json() == {"id": draft.id}


def test_next_follows_filename_order(client: TestClient, seed: SimpleNamespace) -> None:
    a = seed.image(created_at=_t(1))
    seed.original_filename(a, "a.png")
    b = seed.image(created_at=_t(2))
    seed.original_filename(b, "b.png")
    c = seed.image(created_at=_t(3))
    seed.original_filename(c, "c.png")
    unnamed = seed.image(created_at=_t(4))

    params = {"order_by": "original_filename"}
    # the walk follows the listing's order: descending filenames with
    # NULLs last, wrapping around the cycle
    assert client.get(f"/api/images/{c.id}/next", params=params).json() == {"id": b.id}
    assert client.get(f"/api/images/{b.id}/next", params=params).json() == {"id": a.id}
    assert client.get(f"/api/images/{a.id}/next", params=params).json() == {
        "id": unnamed.id
    }
    assert client.get(f"/api/images/{unnamed.id}/next", params=params).json() == {
        "id": c.id
    }
    # prev reverses the walk on the same cycle
    assert client.get(f"/api/images/{b.id}/prev", params=params).json() == {"id": c.id}
    assert client.get(f"/api/images/{a.id}/prev", params=params).json() == {"id": b.id}


def test_next_device_exhausted_returns_null(
    client: TestClient, seed: SimpleNamespace
) -> None:
    only = seed.image()
    seed.device_result(only, checked=True)

    assert client.get(f"/api/images/{only.id}/next").json() == {"id": None}


def test_next_b30_picks_only_incomplete(
    client: TestClient, seed: SimpleNamespace
) -> None:
    done = seed.image(created_at=_t(3))
    seed.b30_result(done, layout=LAYOUT_ID)
    for idx in range(LAYOUT.component_count):
        seed.b30_component(done, idx, checked=True)

    partial = seed.image(created_at=_t(2))
    seed.b30_result(partial, layout=LAYOUT_ID)
    for idx in range(LAYOUT.component_count - 1):
        seed.b30_component(partial, idx, checked=True)

    no_layout = seed.image(created_at=_t(1))
    seed.b30_result(no_layout, layout=None)

    response = client.get(f"/api/images/{done.id}/next", params={"flow": "b30"})
    assert response.json() == {"id": partial.id}
    response = client.get(f"/api/images/{partial.id}/next", params={"flow": "b30"})
    assert response.json() == {"id": no_layout.id}
    # an unknown layout can never count as done, so it stays in the queue.
    # past the tail the scan wraps back to its head
    response = client.get(f"/api/images/{no_layout.id}/next", params={"flow": "b30"})
    assert response.json() == {"id": partial.id}


def test_next_b30_requires_probe_confirmation(
    client: TestClient, seed: SimpleNamespace, probe_layout: ProbeLayout
) -> None:
    canvas_w, canvas_h = LAYOUT.canvas
    candidate = seed.image(created_at=_t(2), width=canvas_w, height=canvas_h)
    current = seed.image(created_at=_t(3), width=None, height=None)

    calls = probe_layout(LAYOUT_ID)
    response = client.get(f"/api/images/{current.id}/next", params={"flow": "b30"})
    assert response.json() == {"id": candidate.id}
    assert calls == [candidate.id]

    # a probe refusal keeps the aspect-matching candidate out of the queue
    probe_layout(None)
    response = client.get(f"/api/images/{current.id}/next", params={"flow": "b30"})
    assert response.json() == {"id": None}


def test_next_b30_scan_bound_hides_older_candidate(
    client: TestClient, seed: SimpleNamespace, probe_layout: ProbeLayout
) -> None:
    canvas_w, canvas_h = LAYOUT.canvas
    current = seed.image(created_at=_t(70), width=None, height=None)
    candidate = seed.image(created_at=_t(9), width=canvas_w, height=canvas_h)
    # aspect-matching fillers occupy the queue ahead of the candidate, the
    # way 16:9 device screenshots share the arcaeaonline B50 canvas aspect
    for minute in range(10, 70):
        seed.image(created_at=_t(minute), width=canvas_w, height=canvas_h)

    calls = probe_layout(
        lambda image_id, relative_path: LAYOUT_ID if image_id == candidate.id else None
    )
    response = client.get(f"/api/images/{current.id}/next", params={"flow": "b30"})
    # each pass is capped at 50 queue candidates and the candidate sits
    # 61st, behind 60 aspect-matching fillers the probe keeps refusing
    assert response.json() == {"id": None}
    assert candidate.id not in calls


def test_next_validates_params_and_current_image(
    client: TestClient, seed: SimpleNamespace
) -> None:
    image = seed.image()

    for params in (
        {"flow": "bogus"},
        {"category": "bogus"},
        {"category": "hidden"},
        {"order_by": "bogus"},
        {"direction": "bogus"},
    ):
        response = client.get(f"/api/images/{image.id}/next", params=params)
        assert response.status_code == 422, params
        prev = client.get(f"/api/images/{image.id}/prev", params=params)
        assert prev.status_code == 422, params
    assert client.get("/api/images/missing-id/next").status_code == 404
    assert client.get("/api/images/missing-id/prev").status_code == 404


def test_next_device_skips_hidden(client: TestClient, seed: SimpleNamespace) -> None:
    done = seed.image(created_at=_t(3))
    seed.device_result(done, checked=True)
    hidden_img = seed.image(created_at=_t(2))
    visible = seed.image(created_at=_t(1))
    _set_hidden(client, hidden_img.id)

    assert client.get(f"/api/images/{done.id}/next").json() == {"id": visible.id}
    # a hidden image can still anchor a scan. It just never comes back
    assert client.get(f"/api/images/{hidden_img.id}/next").json() == {"id": visible.id}


def test_next_b30_skips_hidden(client: TestClient, seed: SimpleNamespace) -> None:
    current = seed.image(created_at=_t(3))
    partial = seed.image(created_at=_t(2))
    seed.b30_result(partial, layout=LAYOUT_ID)
    seed.b30_component(partial, 0, checked=True)
    hidden_img = seed.image(created_at=_t(1))
    seed.b30_result(hidden_img, layout=None)
    _set_hidden(client, hidden_img.id)

    assert client.get(
        f"/api/images/{current.id}/next", params={"flow": "b30"}
    ).json() == {"id": partial.id}
    # past the hidden tail the scan wraps back to the queue head
    assert client.get(
        f"/api/images/{partial.id}/next", params={"flow": "b30"}
    ).json() == {"id": partial.id}
