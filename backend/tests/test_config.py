"""resolve_settings(): source precedence, relative-path bases, and
validation failures. Pure function tests; the module-level snapshot is
not touched."""

from pathlib import Path

import pytest

from app.config import _REPO_ROOT, ConfigError, resolve_settings


def _sqlite_url(path: Path) -> str:
    return f"sqlite:///{path.as_posix()}"


_ENV_NAMES = (
    "ODM_CONFIG",
    "ODM_DATA_DIR",
    "ODM_DATABASE_URL",
    "ODM_IHDB_PATH",
    "ODM_HOST",
    "ODM_PORT",
    "ODM_OPEN_BROWSER",
)


@pytest.fixture(autouse=True)
def clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in _ENV_NAMES:
        monkeypatch.delenv(name, raising=False)


def test_defaults() -> None:
    s = resolve_settings()
    assert s.config_path is None
    assert s.data_dir == _REPO_ROOT / "data"
    assert s.effective_database_url == _sqlite_url(_REPO_ROOT / "data" / "odm.sqlite3")
    assert s.effective_ihdb_path == _REPO_ROOT / "data" / "ihdb.db"
    assert s.host == "127.0.0.1"
    assert s.port == 8199
    assert s.open_browser is True


def test_toml_values_and_relative_base(tmp_path: Path) -> None:
    cfg = tmp_path / "odm.toml"
    cfg.write_text(
        "\n".join(
            [
                'data_dir = "store"',
                'ihdb_path = "hashes.db"',
                'host = "0.0.0.0"',
                "port = 9000",
                "open_browser = false",
                "",
            ]
        ),
        encoding="utf-8",
    )
    s = resolve_settings(config_file=str(cfg))
    assert s.config_path == cfg
    assert s.data_dir == tmp_path / "store"
    assert s.effective_ihdb_path == tmp_path / "hashes.db"
    assert s.host == "0.0.0.0"
    assert s.port == 9000
    assert s.open_browser is False
    assert s.effective_database_url == _sqlite_url(tmp_path / "store" / "odm.sqlite3")


def test_env_overrides_toml(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    cfg = tmp_path / "odm.toml"
    cfg.write_text("port = 9000\n", encoding="utf-8")
    monkeypatch.setenv("ODM_PORT", "9001")
    assert resolve_settings(config_file=str(cfg)).port == 9001


def test_cli_overrides_env_and_toml(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg = tmp_path / "odm.toml"
    cfg.write_text("host = '0.0.0.0'\n", encoding="utf-8")
    monkeypatch.setenv("ODM_HOST", "10.0.0.1")
    s = resolve_settings(config_file=str(cfg), host="192.168.0.1")
    assert s.host == "192.168.0.1"


def test_env_data_dir_is_cwd_relative(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("ODM_DATA_DIR", "store")
    assert resolve_settings().data_dir == tmp_path / "store"


def test_explicit_config_must_exist(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="config file not found"):
        resolve_settings(config_file=str(tmp_path / "missing.toml"))


def test_malformed_toml_is_an_error(tmp_path: Path) -> None:
    cfg = tmp_path / "odm.toml"
    cfg.write_text("data_dir = ", encoding="utf-8")
    with pytest.raises(ConfigError, match="invalid TOML"):
        resolve_settings(config_file=str(cfg))


def test_unknown_toml_key_is_an_error(tmp_path: Path) -> None:
    cfg = tmp_path / "odm.toml"
    cfg.write_text("datadir = 'x'\n", encoding="utf-8")
    with pytest.raises(ConfigError, match="unknown keys"):
        resolve_settings(config_file=str(cfg))


def test_toml_type_errors(tmp_path: Path) -> None:
    bad = tmp_path / "odm.toml"
    bad.write_text("open_browser = 'maybe'\n", encoding="utf-8")
    with pytest.raises(ConfigError, match="open_browser"):
        resolve_settings(config_file=str(bad))

    bad.write_text("port = true\n", encoding="utf-8")
    with pytest.raises(ConfigError, match="port"):
        resolve_settings(config_file=str(bad))


def test_port_range(tmp_path: Path) -> None:
    bad = tmp_path / "odm.toml"
    bad.write_text("port = 70000\n", encoding="utf-8")
    with pytest.raises(ConfigError, match="less than or equal to 65535"):
        resolve_settings(config_file=str(bad))

    with pytest.raises(ConfigError, match="greater than or equal to 1"):
        resolve_settings(port=0)
