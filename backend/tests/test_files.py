from types import SimpleNamespace

from fastapi.testclient import TestClient

from app import storage

IMMUTABLE_CACHE = "public, max-age=31536000, immutable"


def _store_original(image: SimpleNamespace, content: bytes) -> None:
    path = storage.path_for(image.relative_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


def _store_thumb(image_id: str, content: bytes) -> None:
    path = storage.thumb_path_for(image_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


def test_original_file_served_with_immutable_cache(
    client: TestClient, seed: SimpleNamespace
) -> None:
    image = seed.image()
    _store_original(image, b"png-bytes")

    response = client.get(f"/api/images/{image.id}/file")
    assert response.status_code == 200
    assert response.content == b"png-bytes"
    assert response.headers["content-type"] == "image/png"
    assert response.headers["cache-control"] == IMMUTABLE_CACHE


def test_original_file_unknown_image_404(client: TestClient) -> None:
    assert client.get("/api/images/missing-id/file").status_code == 404


def test_original_file_deleted_from_disk_404(
    client: TestClient, seed: SimpleNamespace
) -> None:
    image = seed.image()

    response = client.get(f"/api/images/{image.id}/file")
    assert response.status_code == 404


def test_thumbnail_served_with_immutable_cache(
    client: TestClient, seed: SimpleNamespace
) -> None:
    # the thumbnail endpoint serves whatever sits at the content-addressed
    # path; no image row is consulted
    image = seed.image()
    _store_thumb(image.id, b"thumb-bytes")

    response = client.get(f"/api/images/{image.id}/thumb")
    assert response.status_code == 200
    assert response.content == b"thumb-bytes"
    assert response.headers["content-type"] == "image/jpeg"
    assert response.headers["cache-control"] == IMMUTABLE_CACHE


def test_thumbnail_missing_404(client: TestClient, seed: SimpleNamespace) -> None:
    image = seed.image()

    assert client.get(f"/api/images/{image.id}/thumb").status_code == 404
