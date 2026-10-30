"""`odm` command line entry point: serves the API and the built
frontend from one process.

Keep heavy imports inside `main`, so `--help`/`--version` stay fast
and `apply_settings` runs before any app module binds the config constants.
"""

import argparse
import contextlib
import sys
import threading
import time
import webbrowser
from importlib.metadata import PackageNotFoundError, version
from typing import TYPE_CHECKING

from .config import ConfigError, Settings, resolve_settings

if TYPE_CHECKING:
    import uvicorn


def _cli_version() -> str:
    try:
        return version("odm-backend")
    except PackageNotFoundError:
        return "unknown"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="odm",
        description="Serve the OCR dataset manager in one process.",
    )
    parser.add_argument(
        "--config",
        help="config file to load (default: <anchor>/odm.toml if present)",
    )
    parser.add_argument(
        "--data-dir",
        help="data directory (default: <anchor>/data)",
    )
    parser.add_argument(
        "--host",
        help="bind address (default: 127.0.0.1)",
    )
    parser.add_argument("--port", type=int, help="port (default: 8199)")
    parser.add_argument(
        "--no-open", action="store_true", help="do not open a browser tab on startup"
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {_cli_version()}"
    )
    return parser


def _ensure_data_dir_writable(settings: Settings) -> None:
    """Fail before the server starts: an unwritable data directory
    would otherwise surface as an unrelated database error at first
    write."""
    # a real write, not os.access: the latter ignores ACLs on Windows
    probe = settings.data_dir / ".odm-write-probe"
    try:
        settings.data_dir.mkdir(parents=True, exist_ok=True)
        probe.write_bytes(b"")
    except OSError as e:
        msg = (
            f"data directory is not writable: {settings.data_dir}"
            f"\n  {e}"
            "\n  move the application to a writable location, or choose"
            "\n  another directory via --data-dir or data_dir in odm.toml"
        )
        raise ConfigError(msg) from e
    finally:
        probe.unlink(missing_ok=True)


def _pause_before_exit() -> None:
    """Keep a double-clicked executable's console window open long
    enough for the error to be read."""
    if getattr(sys, "frozen", False) and sys.stdin is not None and sys.stdin.isatty():
        with contextlib.suppress(EOFError, KeyboardInterrupt):
            input("Press Enter to close.")


def _open_browser_when_ready(server: uvicorn.Server, url: str) -> None:
    while not server.started:
        time.sleep(0.1)
    webbrowser.open(url)


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        resolved = resolve_settings(
            config_file=args.config,
            data_dir=args.data_dir,
            host=args.host,
            port=args.port,
            open_browser=False if args.no_open else None,
        )
        _ensure_data_dir_writable(resolved)
    except ConfigError as e:
        print(f"odm: {e}", file=sys.stderr)
        _pause_before_exit()
        return 1

    import uvicorn

    from . import config

    config.apply_settings(resolved)

    # app.main binds the config constants at import. apply_settings
    # must come first
    from .main import app

    display_host = "127.0.0.1" if resolved.host in ("0.0.0.0", "::") else resolved.host
    url = f"http://{display_host}:{resolved.port}"
    print(f"odm {_cli_version()}: serving {url} (data: {resolved.data_dir})")

    server = uvicorn.Server(
        uvicorn.Config(app, host=resolved.host, port=resolved.port, log_level="info")
    )
    if resolved.open_browser:
        opener = threading.Thread(
            target=_open_browser_when_ready, args=(server, url), daemon=True
        )
        opener.start()
    with contextlib.suppress(KeyboardInterrupt):
        server.run()
    return 0
