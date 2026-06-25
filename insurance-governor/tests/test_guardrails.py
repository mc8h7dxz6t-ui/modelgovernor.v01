"""Guardrails and fallback limiter tests."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
SIDECAR = ROOT / "spine" / "sidecar"
sys.path.insert(0, str(SIDECAR))

from tests.conftest_spine import spine_db  # noqa: F401

HEADERS = {"x-internal-token": "test-token"}


@pytest.fixture()
def client(spine_db, monkeypatch):
    from app.config import Settings, override_settings
    from app.guardrails import get_guardrails

    from app.guardrails import reset_guardrails

    reset_guardrails()
    test_settings = Settings(
        database_url="sqlite+pysqlite:///:memory:",
        redis_url="redis://localhost:9/0",
        ig_internal_tokens="test-token",
        guardrails_enabled=True,
        fallback_rate_limit_per_minute=2,
    )
    override_settings(test_settings)
    monkeypatch.setattr("app.config.get_settings", lambda: test_settings)
    get_guardrails.cache_clear()
    from app.main import app

    return TestClient(app)


def test_rate_limit_returns_429(client):
    payload = {
        "platform": "claim_gate",
        "operation_id": "rate-1",
        "account_id": "carrier-default",
        "risk_tier": "high",
        "facets": {"claim_id": "rate-1"},
    }
    assert client.post("/crystallize", headers=HEADERS, json=payload).status_code == 200
    assert client.post("/crystallize", headers=HEADERS, json={**payload, "operation_id": "rate-2"}).status_code == 200
    blocked = client.post("/crystallize", headers=HEADERS, json={**payload, "operation_id": "rate-3"})
    assert blocked.status_code == 429
