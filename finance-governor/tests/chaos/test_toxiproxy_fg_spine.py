"""Toxiproxy chaos — Finance Governor spine survives DB latency."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
import requests
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

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
    migrations = ROOT / "migrations"
    for name in ("0001_fg_spine_init.sql", "0002_fg_hardening.sql", "0003_platform_persistence.sql"):
        sql = (migrations / name).read_text()
        with engine.begin() as conn:
            for stmt in sql.split(";"):
                s = stmt.strip()
                if s and not s.startswith("--"):
                    try:
                        conn.execute(text(s))
                    except Exception:
                        pass


@pytest.fixture()
def chaos_client(monkeypatch):
    url = _pg_url()
    engine = create_engine(url, future=True)
    _apply_schema(engine)

    for name in list(sys.modules):
        if name == "app" or name.startswith("app."):
            del sys.modules[name]
    if str(SIDECAR) not in sys.path:
        sys.path.insert(0, str(SIDECAR))

    from app.config import Settings, get_settings
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


def test_crystallize_survives_db_latency(chaos_client):
    _reset_toxics()
    try:
        requests.post(
            f"{TOXIPROXY_API}/proxies/{PROXY}/toxics",
            json={"name": "latency", "type": "latency", "attributes": {"latency": 50, "jitter": 5}},
            timeout=5,
        ).raise_for_status()
    except requests.RequestException:
        pytest.skip("toxiproxy toxic apply failed")

    facets = {"amount": "10.00"}
    r = chaos_client.post(
        "/crystallize",
        headers=HEADERS,
        json={"platform": "wire_match", "operation_id": "fg-chaos-1", "risk_tier": "high", "facets": facets},
    )
    assert r.status_code == 200
    verify = chaos_client.get("/internal/decisions/verify-chain", headers=HEADERS)
    assert verify.json()["valid"] is True
