"""Platform registry fail-closed when table exists but platform missing."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

ROOT = Path(__file__).resolve().parents[1]
SIDECAR = ROOT / "spine" / "sidecar"
sys.path.insert(0, str(SIDECAR))

from tests.conftest_spine import SCHEMA
from tests.support.fg_migrations import sql_fragments

HEADERS = {"x-internal-token": "test-token"}


@pytest.fixture()
def empty_registry_client(monkeypatch):
    for name in list(sys.modules):
        if name == "app" or name.startswith("app."):
            del sys.modules[name]
    if str(SIDECAR) not in sys.path:
        sys.path.insert(0, str(SIDECAR))

    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    with engine.begin() as conn:
        for fragment in sql_fragments(SCHEMA):
            conn.execute(text(fragment))
        conn.execute(text("DELETE FROM platform_registry"))

    from app.config import Settings
    from app.db import override_engine

    monkeypatch.setattr(
        "app.config.get_settings",
        lambda: Settings(
            database_url="sqlite+pysqlite:///:memory:",
            redis_url="redis://localhost:6380/0",
            fg_internal_tokens="test-token",
        ),
    )
    override_engine(engine)

    from app.main import app

    yield TestClient(app)
    override_engine(create_engine("sqlite+pysqlite:///:memory:", poolclass=StaticPool))


def test_empty_registry_rejects_crystallize(empty_registry_client):
    response = empty_registry_client.post(
        "/crystallize",
        headers=HEADERS,
        json={
            "platform": "wire_match",
            "operation_id": "empty-reg-1",
            "risk_tier": "high",
            "facets": {"amount": "1.00"},
        },
    )
    assert response.status_code == 422
    assert "not registered" in response.json()["detail"]
