import os
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
# repo layout: ocr-dataset-manager/backend/app/config.py

DATA_DIR = Path(os.environ.get("ODM_DATA_DIR", _REPO_ROOT / "data"))
IMAGES_DIR = DATA_DIR / "images"
THUMBS_DIR = DATA_DIR / "thumbs"
PARTNER_ICONS_DIR = DATA_DIR / "partner_icons"
SONGLIST_PATH = DATA_DIR / "catalog" / "songlist"
CHARACTERS_PATH = DATA_DIR / "catalog" / "characters.json"
DATABASE_PATH = DATA_DIR / "odm.sqlite3"
DATABASE_URL = os.environ.get(
    "ODM_DATABASE_URL", f"sqlite:///{DATABASE_PATH.as_posix()}"
)

# built with arcaea_offline_ocr.builders.ihdb.ImageHashesDatabaseBuilder
IHDB_PATH = Path(os.environ.get("ODM_IHDB_PATH", DATA_DIR / "ihdb.db"))
