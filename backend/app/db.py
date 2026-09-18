from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from .config import DATABASE_URL, DATA_DIR

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

BACKEND_DIR = Path(__file__).resolve().parents[1]


def init_db() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    alembic_cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    alembic_cfg.set_main_option(
        "script_location", str(BACKEND_DIR / "migrations")
    )
    command.upgrade(alembic_cfg, "head")


def get_session() -> Session:
    with SessionLocal() as session:
        yield session
