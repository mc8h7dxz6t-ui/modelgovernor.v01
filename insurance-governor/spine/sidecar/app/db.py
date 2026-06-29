from contextlib import contextmanager
from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from .config import get_settings

_engine = None
_read_engine = None
_SessionLocal = None
_ReadSessionLocal = None


def override_engine(engine) -> None:
    global _engine, _SessionLocal
    _engine = engine
    _SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def override_read_engine(engine) -> None:
    global _read_engine, _ReadSessionLocal
    _read_engine = engine
    _ReadSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


@lru_cache(maxsize=1)
def _build_engine():
    settings = get_settings()
    return create_engine(
        settings.database_url,
        pool_pre_ping=True,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_timeout=settings.db_pool_timeout_seconds,
        pool_recycle=settings.db_pool_recycle_seconds,
        future=True,
    )


@lru_cache(maxsize=1)
def _build_read_engine():
    settings = get_settings()
    read_url = settings.database_read_url or settings.database_url
    if read_url.startswith("sqlite"):
        kwargs: dict = {
            "connect_args": {"check_same_thread": False},
            "future": True,
        }
        if ":memory:" in read_url:
            kwargs["poolclass"] = StaticPool
        return create_engine(read_url, **kwargs)
    return create_engine(
        read_url,
        pool_pre_ping=True,
        pool_size=max(2, settings.db_pool_size // 2),
        max_overflow=settings.db_max_overflow,
        pool_timeout=settings.db_pool_timeout_seconds,
        pool_recycle=settings.db_pool_recycle_seconds,
        future=True,
    )


def get_engine():
    global _engine
    if _engine is not None:
        return _engine
    _engine = _build_engine()
    return _engine


def get_read_engine():
    global _read_engine
    settings = get_settings()
    if settings.database_read_url is None:
        return get_engine()
    if _read_engine is not None:
        return _read_engine
    _read_engine = _build_read_engine()
    return _read_engine


def get_session_factory():
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=get_engine(), autoflush=False, autocommit=False)
    return _SessionLocal


def get_read_session_factory():
    global _ReadSessionLocal
    if _ReadSessionLocal is None:
        _ReadSessionLocal = sessionmaker(bind=get_read_engine(), autoflush=False, autocommit=False)
    return _ReadSessionLocal


@contextmanager
def get_db_session() -> Session:
    session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()


@contextmanager
def get_read_db_session() -> Session:
    session = get_read_session_factory()()
    try:
        yield session
    finally:
        session.close()
