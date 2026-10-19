# PyInstaller spec for the portable bundle (onedir: odm.exe + runtime).
# Built from the repository root via backend/scripts/package_windows.py
# (python -m PyInstaller --noconfirm --clean --workpath
# build/pyinstaller --distpath build/dist).
#
# Datas land under sys._MEIPASS (= the onedir _internal directory):
#   web/          built frontend, served by app.main
#   alembic.ini   app.db looks for it at Path(__file__).parents[1],
#                 which is _internal in a frozen app
#   migrations/   alembic scripts, executed as data files at runtime

import shutil
import subprocess
import sys
from pathlib import Path

from PyInstaller.utils.hooks import (
    collect_data_files,
    collect_submodules,
    copy_metadata,
)

spec_dir = Path(SPECPATH).resolve()
frontend_dir = spec_dir / "frontend"
backend_dir = spec_dir / "backend"

# The bundle must never ship stale assets: always build the frontend.
# pnpm is a .cmd shim on Windows; CreateProcess needs its resolved path.
pnpm = shutil.which("pnpm")
if pnpm is None:
    sys.exit("pnpm not found on PATH; it is required to build the frontend")
subprocess.run([pnpm, "build"], cwd=frontend_dir, check=True)

datas = [
    (str(frontend_dir / "dist"), "web"),
    (str(backend_dir / "alembic.ini"), "."),
    (str(backend_dir / "migrations"), "migrations"),
]
datas += collect_data_files("rapidocr")
datas += collect_data_files("arcaea_offline_ocr")
# importlib.metadata.version("odm-backend") in app.cli needs this
datas += copy_metadata("odm-backend")

# rapidocr loads most of its engine modules lazily via importlib at
# runtime, which PyInstaller's static analysis cannot see; collect
# every submodule explicitly.
hiddenimports = collect_submodules("rapidocr")

a = Analysis(
    [str(backend_dir / "app" / "__main__.py")],
    pathex=[str(backend_dir)],
    binaries=None,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    exclude_binaries=True,
    name="odm",
    debug=False,
    strip=False,
    upx=False,
    console=True,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="odm",
)
