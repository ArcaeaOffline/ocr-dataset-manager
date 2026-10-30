"""Path and server settings.

Configuration semantics — precedence, path bases, the anchor
directory — live in the README (Configuration). This module only
discovers, resolves and snapshots them.

The module-level constants are a snapshot of the resolved settings
taken at import (`app.db` binds its engine and the test harness relies
on this snapshot). `apply_settings` re-snapshots them, and the CLI
entry point is its only caller.
"""

import os
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated

from pydantic import BaseModel, Field, ValidationError, field_validator

_REPO_ROOT = Path(__file__).resolve().parents[2]
# repo layout: ocr-dataset-manager/backend/app/config.py

CONFIG_FILENAME = "odm.toml"

# settings whose string values resolve against a base directory (the
# config file's directory for config-file values, the working directory
# otherwise)
_PATH_KEYS = ("data_dir", "ihdb_path")


class ConfigError(Exception):
    """Invalid or missing configuration. The message is user-facing."""


class _SettingsModel(BaseModel):
    """Validated merged values. String paths arrive already resolved
    against their source's base directory."""

    data_dir: Path | None = None
    database_url: Annotated[str | None, Field(min_length=1)] = None
    ihdb_path: Path | None = None
    host: Annotated[str, Field(min_length=1)] = "127.0.0.1"
    port: Annotated[int, Field(ge=1, le=65535)] = 8199
    open_browser: bool = True

    @field_validator("data_dir", "ihdb_path", mode="before")
    @classmethod
    def _non_empty_path(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            raise ValueError("must be a non-empty path")
        return value

    @field_validator("port", mode="before")
    @classmethod
    def _port_not_bool(cls, value: object) -> object:
        # lax mode would coerce true/false to 1/0
        if isinstance(value, bool):
            raise ValueError("must be an integer, not a boolean")
        return value


# one environment variable per field: ODM_ + upper-cased field name
_ENV_NAMES = {name: f"ODM_{name.upper()}" for name in _SettingsModel.model_fields}


@dataclass(frozen=True)
class Settings:
    config_path: Path | None
    data_dir: Path
    database_url: str | None
    ihdb_path: Path | None
    host: str
    port: int
    open_browser: bool
    web_dist_dir: Path | None

    @property
    def effective_database_url(self) -> str:
        if self.database_url is not None:
            return self.database_url
        return f"sqlite:///{(self.data_dir / 'odm.sqlite3').as_posix()}"

    @property
    def effective_ihdb_path(self) -> Path:
        if self.ihdb_path is not None:
            return self.ihdb_path
        return self.data_dir / "ihdb.db"


def anchor_dir() -> Path:
    """Directory the default data location hangs off: the repository
    root in development, the executable's directory when frozen."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return _REPO_ROOT


def _web_dist_dir() -> Path | None:
    """Built frontend bundled with the application, or None when there
    is no frontend build (bare development checkout without one)."""
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass is None:
            return None
        dist = Path(meipass) / "web"
        return dist if (dist / "index.html").is_file() else None
    dist = _REPO_ROOT / "frontend" / "dist"
    return dist if (dist / "index.html").is_file() else None


def _config_location(explicit: str | None) -> Path | None:
    """Config file to load, or None when only defaults and the
    environment apply. An explicitly requested file must exist."""
    if explicit is not None:
        path = Path(explicit)
        if not path.is_file():
            msg = f"config file not found: {path}"
            raise ConfigError(msg)
        return path
    env = os.environ.get("ODM_CONFIG")
    if env:
        path = Path(env)
        if not path.is_file():
            msg = f"config file not found (ODM_CONFIG): {path}"
            raise ConfigError(msg)
        return path
    default = anchor_dir() / CONFIG_FILENAME
    return default if default.is_file() else None


def _load_toml(path: Path) -> dict[str, object]:
    try:
        with path.open("rb") as f:
            parsed = tomllib.load(f)
    except tomllib.TOMLDecodeError as e:
        msg = f"invalid TOML in {path}: {e}"
        raise ConfigError(msg) from e
    allowed = set(_SettingsModel.model_fields)
    unknown = sorted(set(parsed) - allowed)
    if unknown:
        listing = ", ".join(unknown)
        names = ", ".join(sorted(allowed))
        msg = f"unknown keys in {path}: {listing} (expected: {names})"
        raise ConfigError(msg)
    return parsed


def _resolve_path(value: str, base: Path | None) -> Path:
    """Expanduser, then join `base` (None: the current directory)."""
    path = Path(value).expanduser()
    if path.is_absolute():
        return path
    return (base if base is not None else Path.cwd()) / path


def resolve_settings(
    *,
    config_file: str | None = None,
    data_dir: str | None = None,
    database_url: str | None = None,
    ihdb_path: str | None = None,
    host: str | None = None,
    port: int | None = None,
    open_browser: bool | None = None,
) -> Settings:
    config_path = _config_location(config_file)
    toml = _load_toml(config_path) if config_path else {}
    base = config_path.parent if config_path else None

    merged: dict[str, object] = {}
    # lowest to highest: config file, environment, CLI arguments
    for key, value in toml.items():
        if key in _PATH_KEYS and isinstance(value, str):
            merged[key] = _resolve_path(value, base)
        else:
            merged[key] = value
    for key, name in _ENV_NAMES.items():
        if raw := os.environ.get(name):
            merged[key] = _resolve_path(raw, None) if key in _PATH_KEYS else raw
    cli_values: dict[str, object] = {
        "data_dir": data_dir,
        "database_url": database_url,
        "ihdb_path": ihdb_path,
        "host": host,
        "port": port,
        "open_browser": open_browser,
    }
    for key, value in cli_values.items():
        if value is None:
            continue
        if key in _PATH_KEYS and isinstance(value, str):
            merged[key] = _resolve_path(value, None)
        else:
            merged[key] = value

    try:
        validated = _SettingsModel.model_validate(merged)
    except ValidationError as e:
        where = f" in {config_path}" if config_path else ""
        msg = f"invalid settings{where}: {e}"
        raise ConfigError(msg) from e

    return Settings(
        config_path=config_path,
        data_dir=validated.data_dir if validated.data_dir else anchor_dir() / "data",
        database_url=validated.database_url,
        ihdb_path=validated.ihdb_path,
        host=validated.host,
        port=validated.port,
        open_browser=validated.open_browser,
        web_dist_dir=_web_dist_dir(),
    )


settings = resolve_settings()

DATA_DIR = settings.data_dir
IMAGES_DIR = DATA_DIR / "images"
THUMBS_DIR = DATA_DIR / "thumbs"
PARTNER_ICONS_DIR = DATA_DIR / "partner_icons"
SONGLIST_PATH = DATA_DIR / "catalog" / "songlist"
CHARACTERS_PATH = DATA_DIR / "catalog" / "characters.json"
DATABASE_URL = settings.effective_database_url
IHDB_PATH = settings.effective_ihdb_path


def apply_settings(new: Settings) -> None:
    """Re-snapshot the module constants from `new` (see module doc).

    Assignments go through `globals()`: rebinding uppercase names the
    ordinary way reads as a constant redefinition."""
    for name, value in {
        "settings": new,
        "DATA_DIR": new.data_dir,
        "IMAGES_DIR": new.data_dir / "images",
        "THUMBS_DIR": new.data_dir / "thumbs",
        "PARTNER_ICONS_DIR": new.data_dir / "partner_icons",
        "SONGLIST_PATH": new.data_dir / "catalog" / "songlist",
        "CHARACTERS_PATH": new.data_dir / "catalog" / "characters.json",
        "DATABASE_URL": new.effective_database_url,
        "IHDB_PATH": new.effective_ihdb_path,
    }.items():
        globals()[name] = value
