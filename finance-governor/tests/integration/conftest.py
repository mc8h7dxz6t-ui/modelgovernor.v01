"""Postgres integration fixtures — Finance Governor only."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text

ROOT = Path(__file__).resolve().parents[2]
SIDECAR = ROOT / "spine" / "sidecar"
MIGRATIONS = ROOT / "migrations"

POSTGRES_URL = os.environ.get(
    "FG_TEST_DATABASE_URL",
    "postgresql+psycopg://postgres:postgres@localhost:5434/fg_test",
)


def _apply_migrations(engine) -> None:
    for path in sorted(MIGRATIONS.glob("*.sql")):
        sql = path.read_text()
        with engine.begin() as conn:
            conn.execute(text(sql))


@pytest.fixture(scope="session")
def postgres_engine():
    try:
        engine = create_engine(POSTGRES_URL, future=True)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:
        pytest.skip(f"postgres unavailable: {exc}")

    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
    _apply_migrations(engine)
    yield engine
    engine.dispose()


@pytest.fixture()
def pg_sidecar_client(postgres_engine, monkeypatch):
    for name in list(sys.modules):
        if name == "app" or name.startswith("app."):
            del sys.modules[name]
    if str(SIDECAR) not in sys.path:
        sys.path.insert(0, str(SIDECAR))
    elif sys.path[0] != str(SIDECAR):
        sys.path.remove(str(SIDECAR))
        sys.path.insert(0, str(SIDECAR))

    from app.config import Settings
    from app.db import override_engine

    test_settings = Settings(
        database_url=POSTGRES_URL,
        redis_url="redis://localhost:6380/0",
        fg_internal_tokens="test-token",
        oidc_internal_token_is_admin=True,
    )
    monkeypatch.setattr("app.config.get_settings", lambda: test_settings)
    override_engine(postgres_engine)

    from fastapi.testclient import TestClient
    from app.main import app

    return TestClient(app), postgres_engine
