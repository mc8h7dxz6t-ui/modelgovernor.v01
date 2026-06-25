"""Toxiproxy chaos — Finance Governor spine survives DB latency."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
import requests
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

ROOT = Path(__file__).resolve().parents[2]
SIDECAR = ROOT / "spine" / "sidecar"
sys.path.insert(0, str(SIDECAR))
sys.path.insert(0, str(ROOT))

TOXIPROXY_API = os.getenv("FG_TOXIPROXY_API", "http://localhost:8475")
PROXY = "fg-postgres"
HEADERS = {"x-internal-token": "test-token"}


def _pg_url() -> str:
    url = os.getenv("FG_POSTGRES_TEST_URL")
    if not url:
        pytest.skip("FG_POSTGRES_TEST_URL not set — start finance-governor/docker-compose.chaos.yml")
    return url


def _apply_schema(engine) -> None:
    from tests.support.fg_migrations import apply_fg_migrations

    apply_fg_migrations(engine)


@pytest.fixture()
def chaos_client(monkeypatch):
    url = _pg_url()
    engine = create_engine(url, future=True)
    with engine.begin() as conn:
        from sqlalchemy import text

        conn.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
    _apply_schema(engine)

    for name in list(sys.modules):
        if name == "app" or name.startswith("app."):
            del sys.modules[name]
    if str(SIDECAR) not in sys.path:
        sys.path.insert(0, str(SIDECAR))

    from app.config import Settings
    from app.db import override_engine

    test_settings = Settings(database_url=url, fg_internal_tokens="test-token")
    monkeypatch.setattr("app.config.get_settings", lambda: test_settings)
    override_engine(engine)

    from app.main import app

    yield TestClient(app)
    override_engine(create_engine("sqlite+pysqlite:///:memory:"))


def _reset_toxics() -> None:
    try:
        requests.delete(f"{TOXIPROXY_API}/proxies/{PROXY}/toxics", timeout=5)
    except requests.RequestException:
        pytest.skip("toxiproxy unavailable")


def _apply_latency(ms: int = 50) -> None:
    try:
        requests.post(
            f"{TOXIPROXY_API}/proxies/{PROXY}/toxics",
            json={"name": "latency", "type": "latency", "attributes": {"latency": ms, "jitter": 5}},
            timeout=5,
        ).raise_for_status()
    except requests.RequestException:
        pytest.skip("toxiproxy toxic apply failed")


def test_crystallize_survives_db_latency(chaos_client):
    _reset_toxics()
    _apply_latency()
    facets = {"amount": "10.00"}
    r = chaos_client.post(
        "/crystallize",
        headers=HEADERS,
        json={"platform": "wire_match", "operation_id": "fg-chaos-1", "risk_tier": "high", "facets": facets},
    )
    assert r.status_code == 200
    verify = chaos_client.get("/internal/decisions/verify-chain", headers=HEADERS)
    assert verify.json()["valid"] is True


def test_credit_lifecycle_survives_db_latency(chaos_client):
    _reset_toxics()
    _apply_latency(80)
    facets = {
        "application_id": "fg-chaos-credit-1",
        "exposure_amount": "5000.00",
        "model_version_id": "credit-model-v3",
        "desk_id": "desk-default",
    }
    cry = chaos_client.post(
        "/crystallize",
        headers=HEADERS,
        json={
            "platform": "credit_govern",
            "operation_id": "fg-chaos-credit-1",
            "account_id": "desk-default",
            "risk_tier": "high",
            "facets": facets,
            "policy_id": "credit-high-us",
            "reserved_exposure": "5000.00",
        },
    )
    assert cry.status_code == 200, cry.text
    crystal_id = cry.json()["crystal_id"]
    commit = chaos_client.post(
        "/commit",
        headers=HEADERS,
        json={
            "crystal_id": crystal_id,
            "facets": {**facets, "score": 0.82, "explanation_id": "exp-chaos"},
            "committed_exposure": "5000.00",
            "outcome": "approved",
        },
    )
    assert commit.status_code == 200, commit.text
    verify = chaos_client.get("/internal/decisions/verify-chain", headers=HEADERS)
    assert verify.json()["valid"] is True
