"""SPA static serving: file responses, index.html fallback for
client-side routes, API 404 passthrough, and traversal rejection."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.main import register_spa


def _client(tmp_path: Path) -> TestClient:
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<html>index</html>", encoding="utf-8")
    (dist / "assets" / "app.js").write_text("console.log(1);", encoding="utf-8")
    (dist / "favicon.svg").write_text("<svg/>", encoding="utf-8")
    app = FastAPI()
    register_spa(app, dist)
    return TestClient(app)


def test_serves_index_and_static_files(tmp_path: Path) -> None:
    client = _client(tmp_path)

    response = client.get("/")
    assert response.status_code == 200
    assert response.text == "<html>index</html>"
    assert response.headers["content-type"].startswith("text/html")

    response = client.get("/assets/app.js")
    assert response.status_code == 200
    assert "javascript" in response.headers["content-type"]

    response = client.get("/favicon.svg")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("image/svg")


def test_unknown_paths_fall_back_to_index(tmp_path: Path) -> None:
    client = _client(tmp_path)
    for path in ("/annotate", "/annotate/123", "/annotate?x=1"):
        response = client.get(path)
        assert response.status_code == 200
        assert response.text == "<html>index</html>"


def test_api_prefix_stays_json_404(tmp_path: Path) -> None:
    client = _client(tmp_path)
    response = client.get("/api/nope")
    assert response.status_code == 404
    assert response.json() == {"detail": "Not Found"}


def test_traversal_stays_inside_dist(tmp_path: Path) -> None:
    secret = tmp_path / "secret.txt"
    secret.write_text("secret", encoding="utf-8")
    client = _client(tmp_path)

    response = client.get("/assets/../../secret.txt")
    assert response.status_code == 200
    assert response.text == "<html>index</html>"
