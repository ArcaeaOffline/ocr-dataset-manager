"""Song / partner catalogs for annotation helpers.

Song data comes from the game's songlist file and partner icons from the
extracted asset directory; both live under data/ (not in version
control). Partner ids are the icon filename stems, which is the same
labeling the ihdb was built with, so candidates and icons always align.
"""

import json
import logging
import re
from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from ..config import PARTNER_ICONS_DIR, SONGLIST_PATH

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/catalog", tags=["catalog"])

_PARTNER_ID_RE = re.compile(r"^\d+u?$")


@lru_cache(maxsize=4)
def _parse_songlist(path: Path, _mtime: int) -> list[dict[str, str]]:
    # _mtime is unused in the body; it is the cache key that triggers a
    # re-parse when the songlist file changes on disk
    data = json.loads(path.read_text(encoding="utf-8"))
    songs: list[dict[str, str]] = []
    for entry in data.get("songs", []):
        song_id = entry.get("id")
        title = (entry.get("title_localized") or {}).get("en")
        if song_id and title:
            songs.append({"id": song_id, "title": title})
    return songs


@router.get("/songs")
def list_songs() -> list[dict[str, str]]:
    if not SONGLIST_PATH.exists():
        return []
    return _parse_songlist(SONGLIST_PATH, int(SONGLIST_PATH.stat().st_mtime))


@router.get("/partners")
def list_partners() -> list[dict[str, str]]:
    ids = sorted(
        (p.stem for p in PARTNER_ICONS_DIR.iterdir() if p.is_file()),
        key=lambda s: (int(s.rstrip("u")), s.endswith("u")),
    )
    return [{"id": i} for i in ids]


@router.get("/partners/{partner_id}/icon")
def partner_icon(partner_id: str) -> FileResponse:
    if not _PARTNER_ID_RE.match(partner_id):
        raise HTTPException(status_code=404, detail="unknown partner")
    for ext in (".png", ".jpg"):
        path = PARTNER_ICONS_DIR / f"{partner_id}{ext}"
        if path.exists():
            media_type = "image/png" if ext == ".png" else "image/jpeg"
            return FileResponse(path, media_type=media_type)
    raise HTTPException(status_code=404, detail="icon not found")
