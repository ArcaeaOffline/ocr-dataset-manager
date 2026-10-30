"""The annotate view's cropped-image and ROI geometry endpoints.

An explicit `rois_type` skips layout detection, so a stored synthetic
image exercises the geometry path on any machine. No fixture in this
suite passes real detection, so the detection path is asserted only
through its undetectable-image 422.
"""

from typing import TYPE_CHECKING

import cv2
import numpy as np
from fastapi.testclient import TestClient

from app import storage

if TYPE_CHECKING:
    from types import SimpleNamespace

IMMUTABLE_CACHE = "public, max-age=31536000, immutable"

_FLAT_IMAGE = np.full((1280, 720, 3), 200, dtype=np.uint8)


def _store_png(image: "SimpleNamespace", arr: np.ndarray) -> None:
    ok, buf = cv2.imencode(".png", arr)
    assert ok
    path = storage.path_for(image.relative_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(buf.tobytes())


def test_cropped_serves_decodable_jpeg_with_immutable_cache(
    client: TestClient, seed: "SimpleNamespace"
) -> None:
    image = seed.image()
    _store_png(image, _FLAT_IMAGE)

    response = client.get(f"/api/images/{image.id}/cropped")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/jpeg"
    assert response.headers["cache-control"] == IMMUTABLE_CACHE
    decoded = cv2.imdecode(
        np.frombuffer(response.content, dtype=np.uint8), cv2.IMREAD_COLOR
    )
    assert decoded is not None
    # a uniform image has no black edges: the crop is the stored size
    assert decoded.shape[:2] == (1280, 720)


def test_cropped_unknown_image_404(client: TestClient) -> None:
    assert client.get("/api/images/missing-id/cropped").status_code == 404


def test_device_rois_explicit_rois_type_skips_detection(
    client: TestClient, seed: "SimpleNamespace"
) -> None:
    image = seed.image()
    _store_png(image, _FLAT_IMAGE)

    response = client.get(
        f"/api/images/{image.id}/device_rois", params={"rois_type": 0}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["rois_type"] == 0
    assert body["canvas"] == [720, 1280]
    assert set(body["rects"]) == {
        "score",
        "pure",
        "far",
        "lost",
        "max_recall",
        "pure_shiny",
        "high_score",
        "high_score_delta",
        "early_late",
        "rating_class",
        "clear_status",
    }
    assert all(
        len(rect) == 4 and all(isinstance(n, int) for n in rect)
        for rect in body["rects"].values()
    )


def test_device_rois_t2_differs_from_t1(
    client: TestClient, seed: "SimpleNamespace"
) -> None:
    image = seed.image()
    _store_png(image, _FLAT_IMAGE)

    t1 = client.get(
        f"/api/images/{image.id}/device_rois", params={"rois_type": 0}
    ).json()["rects"]
    t2 = client.get(
        f"/api/images/{image.id}/device_rois", params={"rois_type": 1}
    ).json()["rects"]
    assert t2 != t1


def test_device_rois_undetectable_422(
    client: TestClient, seed: "SimpleNamespace"
) -> None:
    # a flat bright image carries no T1/T2 structure
    image = seed.image()
    _store_png(image, _FLAT_IMAGE)

    response = client.get(f"/api/images/{image.id}/device_rois")
    assert response.status_code == 422


def test_device_rois_invalid_rois_type_422(
    client: TestClient, seed: "SimpleNamespace"
) -> None:
    image = seed.image()
    _store_png(image, _FLAT_IMAGE)

    response = client.get(
        f"/api/images/{image.id}/device_rois", params={"rois_type": 5}
    )
    assert response.status_code == 422


def test_device_rois_unknown_image_404(client: TestClient) -> None:
    assert client.get("/api/images/missing-id/device_rois").status_code == 404
