"""Extract partner icons and the songlist from an Arcaea APK into the
backend data directory."""

import re
import sys
import zipfile
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
PARTNER_ICONS_DIR = DATA_DIR / "partner_icons"
SONGLIST_PATH = DATA_DIR / "catalog" / "songlist"

# same interest rules as the reference extractor; icon stems double as
# ihdb labels
_PARTNER_ICON = re.compile(r"^assets/char/(\d+u?)_icon\.(jpg|png)$")
_SONGLIST = re.compile(r"^assets/songs/songlist$")


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

    print(f"{icons} partner icons -> {PARTNER_ICONS_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
