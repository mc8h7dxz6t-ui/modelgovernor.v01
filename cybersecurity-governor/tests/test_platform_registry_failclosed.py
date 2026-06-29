"""Platform registry fail-closed when table exists but platform missing."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool

ROOT = Path(__file__).resolve().parents[1]
SIDECAR = ROOT / "spine" / "sidecar"
sys.path.insert(0, str(SIDECAR))

from tests.conftest_spine import SCHEMA
from support.cg_migrations import sql_fragments
from support.cyber_fixtures import EGRESS_PLATFORM, egress_facets

HEADERS = {"x-internal-token": "test-token"}


@pytest.fixture()
def empty_registry_client(monkeypatch):
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

    from app.config import Settings, get_settings, override_settings
    from app.db import override_engine
    from app.guardrails import reset_guardrails

    test_settings = Settings(
        database_url="sqlite+pysqlite:///:memory:",
        redis_url="redis://localhost:6381/0",
        cg_internal_tokens="test-token",
        platform_registry_enforce=True,
    )
    override_settings(test_settings)
    monkeypatch.setattr("app.config.get_settings", get_settings)
    override_engine(engine)
    reset_guardrails()

    from app.main import app

    yield TestClient(app)


def test_empty_registry_rejects_crystallize(empty_registry_client):
    response = empty_registry_client.post(
        "/crystallize",
        headers=HEADERS,
        json={
            "platform": EGRESS_PLATFORM,
            "operation_id": "empty-reg-1",
            "risk_tier": "high",
            "facets": egress_facets(flow_id="empty-reg-1"),
        },
    )
    assert response.status_code == 422
    assert "not registered" in response.json()["detail"]
