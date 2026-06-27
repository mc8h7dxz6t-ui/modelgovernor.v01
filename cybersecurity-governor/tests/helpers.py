"""Shared test helpers for Cybersecurity Governor spine."""
from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

ROOT = Path(__file__).resolve().parents[1]
SIDECAR = ROOT / "spine" / "sidecar"
if str(SIDECAR) not in sys.path:
    sys.path.insert(0, str(SIDECAR))

SCHEMA_SQLITE = (ROOT / "tests" / "schema_sqlite.sql").read_text(encoding="utf-8")


def cg_settings(database_url: str, **overrides):
    from app.config import Settings

    defaults = {
        "database_url": database_url,
        "redis_url": "redis://localhost:6381/0",
        "cg_internal_tokens": "test-token",
        "commit_ttl_seconds": 300,
    }
    defaults.update(overrides)
    return Settings(**defaults)


def apply_sqlite_schema(engine: Engine) -> None:
    with engine.begin() as conn:
        for stmt in SCHEMA_SQLITE.split(";"):
            s = stmt.strip()
            if s:
                conn.execute(text(s))


def create_sqlite_engine(path: Path) -> Engine:
    engine = create_engine(
        f"sqlite+pysqlite:///{path}",
        connect_args={"check_same_thread": False},
        future=True,
    )
    apply_sqlite_schema(engine)
    return engine


def session_factory(engine: Engine):
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
