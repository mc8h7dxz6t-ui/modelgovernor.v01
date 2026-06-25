from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from .config import get_settings

_ENGINE: Engine | None = None
_SESSION_FACTORY = sessionmaker(autoflush=False, autocommit=False, future=True)


def get_engine() -> Engine:
    global _ENGINE
    if _ENGINE is None:
        url = get_settings().database_url
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+psycopg://", 1)
        _ENGINE = create_engine(url, future=True, pool_pre_ping=True)
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
