"""Local-disk image storage.

The database only ever stores paths relative to IMAGES_DIR; switching to
another backend later means reimplementing this module only.
"""

import shutil
from hashlib import sha256
from pathlib import Path

import cv2
import numpy as np

from .config import IMAGES_DIR, THUMBS_DIR

THUMB_HEIGHT = 256
HASH_SIZE = 16


def file_sha256(path: Path) -> str:
    h = sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def average_image_hash(img_bgr) -> str:
    """Whole-image perceptual hash (16x16 average hasher, hex-packed bits).

    Non-unique by design; only used for near-duplicate warnings."""
    from arcaea_offline_ocr.core import hashers  # noqa: PLC0415

    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    mat = hashers.average(gray, HASH_SIZE)
    return np.packbits(mat.flatten()).tobytes().hex()


def path_for(relative_path: str) -> Path:
    return IMAGES_DIR / relative_path


def thumb_path_for(image_id: str) -> Path:
    return THUMBS_DIR / image_id[:2] / f"{image_id}.jpg"


def relative_path_for(image_id: str, extension: str) -> str:
    extension = extension.lstrip(".").lower()
    return f"{image_id[:2]}/{image_id}.{extension}"


def import_image(source: Path, image_id: str) -> tuple[str, int, int]:
    """Copy `source` into storage under `image_id`.

    Returns (relative_path, width, height). Callers handle the content hash
    themselves so duplicates can be rejected before any copy happens.
    """
    dest = path_for(relative_path_for(image_id, source.suffix))
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, dest)

    img = cv2.imread(str(dest))
    if img is None:
        dest.unlink()
        msg = f"not a readable image: {source}"
        raise ValueError(msg)
    h, w = img.shape[:2]
    return (dest.relative_to(IMAGES_DIR).as_posix(), w, h)


def save_thumbnail(img_bgr, image_id: str) -> str:
    dest = thumb_path_for(image_id)
    dest.parent.mkdir(parents=True, exist_ok=True)
    h, w = img_bgr.shape[:2]
    scale = THUMB_HEIGHT / h
    thumb = cv2.resize(img_bgr, (max(1, round(w * scale)), THUMB_HEIGHT))
    cv2.imwrite(str(dest), thumb, [cv2.IMWRITE_JPEG_QUALITY, 85])
    return str(dest.relative_to(THUMBS_DIR).as_posix())
