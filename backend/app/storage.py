"""Local-disk image storage.

The database only ever stores paths relative to IMAGES_DIR; switching to
another backend later means reimplementing this module only.
"""

import shutil
from hashlib import sha256
from pathlib import Path

from .config import IMAGES_DIR


def file_sha256(path: Path) -> str:
    h = sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def path_for(relative_path: str) -> Path:
    return IMAGES_DIR / relative_path


def relative_path_for(image_id: str, extension: str) -> str:
    extension = extension.lstrip(".").lower()
    return f"{image_id[:2]}/{image_id}.{extension}"


def import_image(source: Path, image_id: str) -> tuple[str, str, int, int]:
    """Copy `source` into storage under `image_id`.

    Returns (relative_path, sha256, width, height).
    """
    from cv2.typing import MatLike  # noqa: PLC0415

    import cv2  # noqa: PLC0415

    dest = path_for(relative_path_for(image_id, source.suffix))
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, dest)

    img: MatLike | None = cv2.imread(str(dest))
    if img is None:
        dest.unlink()
        msg = f"not a readable image: {source}"
        raise ValueError(msg)
    h, w = img.shape[:2]
    return (dest.relative_to(IMAGES_DIR).as_posix(), file_sha256(dest), w, h)
