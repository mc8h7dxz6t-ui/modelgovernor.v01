"""Postgres fixtures for Cybersecurity Governor integration tests."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

ROOT = Path(__file__).resolve().parents[2]
SIDECAR = ROOT / "spine" / "sidecar"
sys.path.insert(0, str(SIDECAR))
sys.path.insert(0, str(ROOT))

from tests.helpers import apply_postgres_migrations, cg_settings, reset_cg_tables

POSTGRES_URL = os.environ.get(
    "CG_POSTGRES_TEST_URL",
    os.environ.get("POSTGRES_TEST_URL", ""),
)


@pytest.fixture(scope="session")
def pg_engine() -> Engine:
    if not POSTGRES_URL:
        pytest.skip("CG_POSTGRES_TEST_URL not set")
    url = POSTGRES_URL
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    engine = create_engine(url, future=True, pool_pre_ping=True)
    apply_postgres_migrations(engine)
    yield engine
    engine.dispose()


@pytest.fixture()
def pg_settings(pg_engine, monkeypatch):
    from app.config import Settings, get_settings

    test_settings = Settings(
        database_url=str(pg_engine.url),
        redis_url="redis://localhost:6390/0",
        cg_internal_tokens="test-token",
        oidc_enabled=False,
    )
    get_settings.cache_clear()
    monkeypatch.setattr("app.config.get_settings", lambda: test_settings)
    monkeypatch.setattr("app.auth_oidc.get_settings", lambda: test_settings)
    return test_settings


@pytest.fixture()
def clean_cg_tables(pg_engine: Engine):
    reset_cg_tables(pg_engine)
    yield

