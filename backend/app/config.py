import os
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
# repo layout: ocr-dataset-manager/backend/app/config.py
_ARCAEA_OFFLINE_ROOT = _REPO_ROOT.parent

DATA_DIR = Path(os.environ.get("ODM_DATA_DIR", _REPO_ROOT / "data"))
IMAGES_DIR = DATA_DIR / "images"
THUMBS_DIR = DATA_DIR / "thumbs"
DATABASE_PATH = DATA_DIR / "odm.sqlite3"
DATABASE_URL = os.environ.get(
    "ODM_DATABASE_URL", f"sqlite:///{DATABASE_PATH.as_posix()}"
)

IHDB_PATH = Path(
    os.environ.get(
        "ODM_IHDB_PATH",
        _ARCAEA_OFFLINE_ROOT / "core-ocr" / "__debug" / "ihdb-7.0.255.db",
    )
)
CRNN_MODEL_PATH = Path(
    os.environ.get(
        "ODM_CRNN_MODEL_PATH",
        _ARCAEA_OFFLINE_ROOT / "core-ocr" / "assets" / "ocr" / "model_patched.onnx",
    )
)
