"""Build the Windows portable bundle with PyInstaller.

Run from the repository root: uv run backend/scripts/package_windows.py

Requires pnpm (the frontend build runs inside odm.spec). Output:
build/dist/odm/.
"""

import os
import subprocess
import sys
from pathlib import Path

# the PyInstaller command below uses repo-root-relative paths
# but uv run may be invoked from anywhere
os.chdir(Path(__file__).resolve().parents[2])

subprocess.run(
    [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--workpath",
        "build/pyinstaller",
        "--distpath",
        "build/dist",
        "odm.spec",
    ],
    check=True,
)

print()
print("bundle: build/dist/odm/odm.exe")
