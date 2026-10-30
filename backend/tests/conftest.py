"""Test harness: tmp data dir + database, one TestClient, per-test reset.

`app.config` snapshots its paths and `app.db` binds its engine at import
time, so the env vars and the sys.path insert precede the first `app`
import."""

import atexit
import itertools
import os
import shutil
import sys
import tempfile
import uuid
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from typing import TypeVar

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import inspect

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

_DATA_DIR = Path(tempfile.mkdtemp(prefix="odm-tests-"))
os.environ["ODM_DATA_DIR"] = _DATA_DIR.as_posix()
os.environ["ODM_DATABASE_URL"] = f"sqlite:///{(_DATA_DIR / 'odm.sqlite3').as_posix()}"

# the real-OCR smoke needs an ihdb in the data dir. Seed one from the
# repository's runtime copy so the smoke runs on machines that have it
# and skips otherwise (CI)
if "ODM_IHDB_PATH" not in os.environ:
    _ihdb = Path(__file__).resolve().parents[2] / "data" / "ihdb.db"
    if _ihdb.is_file():
        shutil.copy(_ihdb, _DATA_DIR / "ihdb.db")

atexit.register(shutil.rmtree, _DATA_DIR, True)


@pytest.fixture(scope="session")
def client() -> Iterator[TestClient]:
    from app.main import app

    # entering the context runs the lifespan, whose init_db() applies all
    # migrations to the fresh tmp database
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def isolated_state(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Fresh database rows, prefill caches and data files per test. The
    import thread's queue warm-up never runs real OCR."""
    from app.services import prefill

    monkeypatch.setattr(prefill, "warm", lambda _pending: None)
    yield

    from app.config import DATA_DIR
    from app.db import SessionLocal, engine
    from app.models import Base
    from app.routers import catalog as catalog_router

    # the real-OCR smoke runs without the client fixture, so the tmp
    # database may never have been migrated
    if inspect(engine).has_table("images"):
        with SessionLocal() as session:
            for table in reversed(Base.metadata.sorted_tables):
                session.execute(table.delete())
            session.commit()
    prefill._cache.clear()
    prefill._b30_layouts.clear()
    prefill._b30_components.clear()
    catalog_router._parse_songlist.cache_clear()
    catalog_router._parse_characters.cache_clear()
    for name in ("images", "thumbs", "partner_icons", "catalog"):
        shutil.rmtree(DATA_DIR / name, ignore_errors=True)


T = TypeVar("T")


@pytest.fixture
def seed() -> SimpleNamespace:
    """Row factories writing straight through SessionLocal. Each call
    commits and returns the inserted ORM row."""
    from app.db import SessionLocal
    from app.models import B30Component, B30Result, DeviceResult, Image

    counter = itertools.count()

    def _save(row: T) -> T:
        with SessionLocal() as session:
            session.add(row)
            session.commit()
        return row

    def image(
        *,
        created_at: datetime | None = None,
        width: int | None = 1080,
        height: int | None = 1920,
    ) -> Image:
        image_id = uuid.uuid4().hex
        return _save(
            Image(
                id=image_id,
                relative_path=f"seed/{next(counter):04d}/{image_id}.png",
                sha256=uuid.uuid4().hex,
                width=width,
                height=height,
                created_at=created_at or datetime(2026, 1, 1),
            )
        )

    def device_result(
        image: Image, *, checked: bool = False, **fields: object
    ) -> DeviceResult:
        row = DeviceResult(image_id=image.id, checked=checked)
        for name, value in fields.items():
            setattr(row, name, value)
        return _save(row)

    def b30_result(image: Image, *, layout: str | None = None) -> B30Result:
        return _save(B30Result(image_id=image.id, layout=layout))

    def b30_component(
        image: Image, index: int, *, checked: bool = False, **fields: object
    ) -> B30Component:
        row = B30Component(image_id=image.id, component_index=index, checked=checked)
        for name, value in fields.items():
            setattr(row, name, value)
        return _save(row)

    return SimpleNamespace(
        image=image,
        device_result=device_result,
        b30_result=b30_result,
        b30_component=b30_component,
    )
