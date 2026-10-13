import json
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def songlist() -> Path:
    from app.config import SONGLIST_PATH

    SONGLIST_PATH.parent.mkdir(parents=True, exist_ok=True)
    return SONGLIST_PATH


@pytest.fixture
def partner_icons() -> Path:
    from app.config import PARTNER_ICONS_DIR

    PARTNER_ICONS_DIR.mkdir(parents=True, exist_ok=True)
    return PARTNER_ICONS_DIR


def test_songs_keeps_entries_with_id_and_en_title(
    client: TestClient, songlist: Path
) -> None:
    songlist.write_text(
        json.dumps(
            {
                "songs": [
                    {"id": "song_a", "title_localized": {"en": "Song A"}},
                    {"id": "song_b", "title_localized": {"ja": "ジャ", "en": "Song B"}},
                    {"id": None, "title_localized": {"en": "no id"}},
                    {"id": "song_c", "title_localized": {}},
                ]
            }
        ),
        encoding="utf-8",
    )
    assert client.get("/api/catalog/songs").json() == [
        {"id": "song_a", "title": "Song A"},
        {"id": "song_b", "title": "Song B"},
    ]


def test_songs_without_songlist_file_returns_empty_list(client: TestClient) -> None:
    assert client.get("/api/catalog/songs").json() == []


def test_songs_reparse_when_file_mtime_changes(
    client: TestClient, songlist: Path
) -> None:
    # the parse cache is keyed on (path, mtime); force well-separated
    # mtimes so the second read cannot collide with the first
    songlist.write_text(
        json.dumps({"songs": [{"id": "a", "title_localized": {"en": "A"}}]}),
        encoding="utf-8",
    )
    os.utime(songlist, (1_500_000_000, 1_500_000_000))
    assert client.get("/api/catalog/songs").json() == [{"id": "a", "title": "A"}]

    songlist.write_text(
        json.dumps({"songs": [{"id": "b", "title_localized": {"en": "B"}}]}),
        encoding="utf-8",
    )
    os.utime(songlist, (1_600_000_000, 1_600_000_000))
    assert client.get("/api/catalog/songs").json() == [{"id": "b", "title": "B"}]


def test_partners_sorted_by_numeric_id_with_u_suffix_last(
    client: TestClient, partner_icons: Path
) -> None:
    for name in ("10.png", "1.png", "10u.jpg", "2.png", "2u.png"):
        (partner_icons / name).write_bytes(b"x")
    response = client.get("/api/catalog/partners")
    assert [p["id"] for p in response.json()] == ["1", "2", "2u", "10", "10u"]


def test_partner_icon_prefers_png_over_jpg(
    client: TestClient, partner_icons: Path
) -> None:
    (partner_icons / "5.png").write_bytes(b"png-bytes")
    (partner_icons / "5.jpg").write_bytes(b"jpg-bytes")
    response = client.get("/api/catalog/partners/5/icon")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert response.content == b"png-bytes"


def test_partner_icon_serves_jpg_when_png_missing(
    client: TestClient, partner_icons: Path
) -> None:
    (partner_icons / "7.jpg").write_bytes(b"jpg-bytes")
    response = client.get("/api/catalog/partners/7/icon")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/jpeg"


def test_partner_icon_rejects_malformed_id(
    client: TestClient, partner_icons: Path
) -> None:
    (partner_icons / "1.png").write_bytes(b"png-bytes")
    assert client.get("/api/catalog/partners/abc/icon").status_code == 404


def test_partner_icon_unknown_partner_404(
    client: TestClient, partner_icons: Path
) -> None:
    (partner_icons / "1.png").write_bytes(b"png-bytes")
    assert client.get("/api/catalog/partners/9/icon").status_code == 404
