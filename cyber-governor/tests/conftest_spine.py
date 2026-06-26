"""Spine integration test fixtures."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine, event, text
from sqlalchemy.pool import StaticPool

ROOT = Path(__file__).resolve().parents[1]
SIDECAR = ROOT / "spine" / "sidecar"
if str(SIDECAR) not in sys.path:
    sys.path.insert(0, str(SIDECAR))

SCHEMA = (Path(__file__).parent / "schema_sqlite.sql").read_text()


@pytest.fixture()
def spine_db(monkeypatch):
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    with engine.begin() as conn:
        for stmt in SCHEMA.split(";"):
            s = stmt.strip()
            if s:
                conn.execute(text(s))

    from app.config import Settings, get_settings
    from app.db import override_engine

    test_settings = Settings(
        database_url="sqlite+pysqlite:///:memory:",
        redis_url="redis://localhost:6390/0",
        cg_internal_tokens="test-token",
        oidc_enabled=False,
    )
    get_settings.cache_clear()
    monkeypatch.setattr("app.config.get_settings", lambda: test_settings)
    monkeypatch.setattr("app.auth_oidc.get_settings", lambda: test_settings)
    override_engine(engine)
    yield engine
    override_engine(create_engine("sqlite+pysqlite:///:memory:", poolclass=StaticPool))
