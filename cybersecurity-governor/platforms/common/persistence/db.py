"""Platform database connectivity — uses PgBouncer URL in production."""
from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Iterator

try:
    import psycopg
except ImportError:  # pragma: no cover
    psycopg = None  # type: ignore[assignment]


def platform_db_enabled() -> bool:
    return bool(_dsn())


def _dsn() -> str:
    raw = os.environ.get("CG_PLATFORM_DATABASE_URL") or os.environ.get("DATABASE_URL", "")
    return raw.replace("postgresql+psycopg://", "postgresql://")


@contextmanager
def platform_connection() -> Iterator["psycopg.Connection | None"]:
    dsn = _dsn()
    if not dsn or psycopg is None:
        yield None
        return
    with psycopg.connect(dsn, autocommit=False) as conn:
        yield conn
