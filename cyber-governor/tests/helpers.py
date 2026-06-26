"""Shared test helpers for Cybersecurity Governor spine."""
from __future__ import annotations

import sys
from decimal import Decimal
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

ROOT = Path(__file__).resolve().parents[1]
SIDECAR = ROOT / "spine" / "sidecar"
if str(SIDECAR) not in sys.path:
    sys.path.insert(0, str(SIDECAR))

SCHEMA_SQLITE = (ROOT / "tests" / "schema_sqlite.sql").read_text(encoding="utf-8")
MIGRATIONS_DIR = ROOT / "migrations"


def cg_settings(database_url: str, **overrides):
    from app.config import Settings

    defaults = {
        "database_url": database_url,
        "redis_url": "redis://localhost:6390/0",
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


def apply_postgres_migrations(engine: Engine) -> None:
    with engine.begin() as conn:
        for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
            sql = path.read_text(encoding="utf-8")
            conn.execute(text(sql))


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


def identity_facets(**extra) -> dict:
    base = {
        "user_id": "alice@corp.example",
        "device_fingerprint": "dev_fp_trusted",
        "session_state": "AUTHORIZED",
    }
    base.update(extra)
    return base
