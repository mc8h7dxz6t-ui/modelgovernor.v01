"""Tier 2 — Postgres vigorous tests for Cybersecurity Governor spine."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text

ROOT = Path(__file__).resolve().parents[1]
SIDECAR = ROOT / "spine" / "sidecar"
sys.path.insert(0, str(SIDECAR))

POSTGRES_URL = os.environ.get(
    "CG_POSTGRES_TEST_URL",
    os.environ.get("POSTGRES_TEST_URL", ""),
)


pytestmark = pytest.mark.skipif(not POSTGRES_URL, reason="CG_POSTGRES_TEST_URL not set")


@pytest.fixture(scope="module")
def pg_engine():
    engine = create_engine(POSTGRES_URL, future=True)
    migrations = sorted((ROOT / "migrations").glob("*.sql"))
    with engine.begin() as conn:
        for path in migrations:
            sql = path.read_text(encoding="utf-8")
            conn.execute(text(sql))
    yield engine
    engine.dispose()


@pytest.fixture()
def pg_session(pg_engine):
    from app.config import Settings
    from app.db import override_engine

    override_engine(pg_engine)
    settings = Settings(database_url=POSTGRES_URL, redis_url="redis://localhost:6390/0", cg_internal_tokens="test")
    yield settings, pg_engine


def test_postgres_crystallize_commit_anchor(pg_session, monkeypatch):
    from fastapi.testclient import TestClient
    from app.config import Settings, get_settings
    from app.main import app

    settings, _ = pg_session
    test_settings = Settings(
        database_url=POSTGRES_URL,
        redis_url="redis://localhost:6390/0",
        cg_internal_tokens="test-token",
    )
    monkeypatch.setattr("app.config.get_settings", lambda: test_settings)
    client = TestClient(app)
    headers = {"x-internal-token": "test-token"}
    facets = {"session_state": "AUTHORIZED", "user_id": "alice@corp.example"}
    cr = client.post(
        "/crystallize",
        headers=headers,
        json={
            "platform": "identity_gate",
            "operation_id": "pg-test-1",
            "account_id": "tenant-default",
            "risk_tier": "critical",
            "facets": facets,
            "policy_id": "identity-critical-us",
        },
    )
    assert cr.status_code == 200, cr.text
    crystal_id = cr.json()["crystal_id"]
    cm = client.post(
        "/commit",
        headers=headers,
        json={"crystal_id": crystal_id, "facets": facets, "outcome": "authorized"},
    )
    assert cm.status_code == 200

    verify = client.get("/internal/security/verify-chain", headers=headers)
    assert verify.status_code == 200
    assert verify.json()["sealed_count"] >= 2

    anchor = client.post("/internal/security/anchor-head", headers=headers)
    assert anchor.status_code == 200
    assert anchor.json()["anchored"] is True
