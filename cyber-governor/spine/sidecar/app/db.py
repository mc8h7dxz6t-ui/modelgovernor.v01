from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from .config import get_settings

_ENGINE: Engine | None = None
_SESSION_FACTORY = sessionmaker(autoflush=False, autocommit=False, future=True)


def build_engine(database_url: str) -> Engine:
    if database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    settings = get_settings()
    kwargs: dict = {"future": True, "pool_pre_ping": True}
    if database_url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
    else:
        kwargs.update(
            pool_size=settings.db_pool_size,
            max_overflow=settings.db_max_overflow,
            pool_timeout=settings.db_pool_timeout_seconds,
            pool_recycle=settings.db_pool_recycle_seconds,
        )
    return create_engine(database_url, **kwargs)


def get_engine() -> Engine:
    global _ENGINE
    if _ENGINE is None:
        _ENGINE = build_engine(get_settings().database_url)
    return _ENGINE


def override_engine(engine: Engine) -> None:
    global _ENGINE
    _ENGINE = engine


@contextmanager
def get_db_session() -> Iterator[Session]:
    session = _SESSION_FACTORY(bind=get_engine())
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
