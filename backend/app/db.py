from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from .config import DATABASE_URL
from .models import Base

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def init_db() -> None:
    from .config import DATA_DIR

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(engine)


def get_session() -> Session:
    with SessionLocal() as session:
        yield session
