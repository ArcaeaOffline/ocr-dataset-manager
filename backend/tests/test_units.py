from pathlib import Path

import cv2
import numpy as np
import pytest

from app import storage
from app.services.imports import new_image_id
from app.services.prefill import _parse_early_late


def test_file_sha256_known_digest(tmp_path: Path) -> None:
    source = tmp_path / "f.bin"
    source.write_bytes(b"abc")

    assert (
        storage.file_sha256(source)
        == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    )


def test_storage_path_conventions() -> None:
    from app.config import IMAGES_DIR, THUMBS_DIR

    image_id = "abcd" * 8
    assert storage.relative_path_for(image_id, ".PNG") == f"ab/{image_id}.png"
    assert storage.thumb_path_for(image_id) == THUMBS_DIR / "ab" / f"{image_id}.jpg"
    assert storage.path_for("xy/logo.png") == IMAGES_DIR / "xy" / "logo.png"


def test_import_image_copies_and_reports_dimensions(tmp_path: Path) -> None:
    source = tmp_path / "shot.png"
    assert cv2.imwrite(str(source), np.full((48, 32, 3), 9, dtype=np.uint8))
    image_id = "abcd" * 8

    relative_path, width, height = storage.import_image(source, image_id)

    assert (width, height) == (32, 48)
    assert relative_path == f"ab/{image_id}.png"
    assert storage.path_for(relative_path).is_file()


def test_import_image_rejects_unreadable_and_cleans_up(tmp_path: Path) -> None:
    source = tmp_path / "broken.png"
    source.write_bytes(b"definitely not an image")
    image_id = "abcd" * 8

    with pytest.raises(ValueError, match="not a readable image"):
        storage.import_image(source, image_id)
    assert not storage.path_for(f"ab/{image_id}.png").exists()


def test_save_thumbnail_scales_to_height_256() -> None:
    image_id = "abcd" * 8

    storage.save_thumbnail(np.full((48, 32, 3), 7, dtype=np.uint8), image_id)

    thumb = cv2.imread(str(storage.thumb_path_for(image_id)))
    assert thumb is not None
    assert thumb.shape[0] == 256
    assert thumb.shape[1] == max(1, round(32 * 256 / 48))


def test_parse_early_late_t2_with_pure_components() -> None:
    parsed = _parse_early_late("L4(P36) E0(P16)", 1)
    assert parsed == {
        "far_late": 4,
        "pure_late": 36,
        "far_early": 0,
        "pure_early": 16,
    }


def test_parse_early_late_t1_has_no_pure_parts() -> None:
    assert _parse_early_late("L1 E5", 0) == {"far_late": 1, "far_early": 5}


def test_parse_early_late_normalizes_letter_o() -> None:
    parsed = _parse_early_late("LO(P22) E3(P1)", 1)
    assert parsed == {
        "far_late": 0,
        "pure_late": 22,
        "far_early": 3,
        "pure_early": 1,
    }


def test_parse_early_late_no_match_returns_none() -> None:
    assert _parse_early_late(None, 1) is None
    assert _parse_early_late("", 1) is None
    assert _parse_early_late("no digits here", 1) is None


def test_new_image_id_unique_32_hex() -> None:
    ids = {new_image_id() for _ in range(8)}

    assert len(ids) == 8
    assert all(len(bytes.fromhex(value)) == 16 for value in ids)
