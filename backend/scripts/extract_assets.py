"""Extract partner icons, the songlist and the characters file from an
Arcaea APK into the backend data directory."""

import re
import sys
import zipfile
from pathlib import Path

from app.config import CHARACTERS_PATH, PARTNER_ICONS_DIR, SONGLIST_PATH

# icon stems double as ihdb labels
_PARTNER_ICON = re.compile(r"^assets/char/(\d+u?)_icon\.(jpg|png)$")
_SONGLIST = re.compile(r"^assets/songs/songlist$")
_CHARACTERS = re.compile(r"^assets/char/characters\.json$")


def main() -> int:
    if len(sys.argv) != 2:
        print(f"usage: {sys.argv[0]} <apk path>")
        return 2
    apk = Path(sys.argv[1])
    if not apk.is_file():
        print(f"not a file: {apk}")
        return 2

    PARTNER_ICONS_DIR.mkdir(parents=True, exist_ok=True)
    SONGLIST_PATH.parent.mkdir(parents=True, exist_ok=True)

    icons = 0
    with zipfile.ZipFile(apk) as zf:
        for name in zf.namelist():
            icon_match = _PARTNER_ICON.match(name)
            if icon_match:
                target = PARTNER_ICONS_DIR / f"{icon_match[1]}.{icon_match[2]}"
                target.write_bytes(zf.read(name))
                icons += 1
                continue
            if _SONGLIST.match(name):
                SONGLIST_PATH.write_bytes(zf.read(name))
                print(f"songlist -> {SONGLIST_PATH}")
            elif _CHARACTERS.match(name):
                CHARACTERS_PATH.write_bytes(zf.read(name))
                print(f"characters -> {CHARACTERS_PATH}")

    print(f"{icons} partner icons -> {PARTNER_ICONS_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
