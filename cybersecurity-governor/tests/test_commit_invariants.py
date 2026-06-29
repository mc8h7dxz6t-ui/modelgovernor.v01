"""CCP surprise-budget invariant counters — behavioral tests."""
from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[1]
SIDECAR = ROOT / "spine" / "sidecar"
sys.path.insert(0, str(SIDECAR))

from tests.conftest_spine import spine_db  # noqa: F401
from support.cyber_fixtures import EGRESS_PLATFORM, egress_facets

HEADERS = {"x-internal-token": "test-token"}


@pytest.fixture()
def client(spine_db):
    from app.main import app

    return TestClient(app)


def _counter(name: str) -> int:
    from app.metrics import get_counters

    return get_counters().snapshot().get(name, 0)


def test_surprise_commit_blocked_unknown_crystal(client):
    facets = egress_facets(flow_id="missing-flow")
    before = _counter("surprise_commit_blocked_total")
    r = client.post(
        "/commit",
        headers=HEADERS,
        json={
            "crystal_id": "missing-crystal",
            "facets": facets,
            "committed_budget": "0",
        },
    )
    assert r.status_code == 409
    assert _counter("surprise_commit_blocked_total") == before + 1


def test_fingerprint_mismatch_increments_counter(client):
    facets = egress_facets(flow_id="inv-fp-1")
    cry = client.post(
        "/crystallize",
        headers=HEADERS,
        json={
            "platform": EGRESS_PLATFORM,
            "operation_id": "inv-fp-1",
            "risk_tier": "high",
            "facets": facets,
        },
    )
    assert cry.status_code == 200
    crystal_id = cry.json()["crystal_id"]
    before = _counter("crystal_fingerprint_mismatch_total")
    bad = client.post(
        "/commit",
        headers=HEADERS,
        json={
            "crystal_id": crystal_id,
            "facets": egress_facets(flow_id="inv-fp-1", host="evil.example.com", decision="DENIED"),
            "committed_budget": "0",
        },
    )
    assert bad.status_code == 409
    assert _counter("crystal_fingerprint_mismatch_total") == before + 1


def test_high_risk_expired_horizon_strands_on_commit(client, spine_db):
    facets = egress_facets(flow_id="inv-horizon-1")
    cry = client.post(
        "/crystallize",
        headers=HEADERS,
        json={
            "platform": EGRESS_PLATFORM,
            "operation_id": "inv-horizon-1",
            "risk_tier": "critical",
            "facets": facets,
        },
    )
    assert cry.status_code == 200
    crystal_id = cry.json()["crystal_id"]
    past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    with spine_db.begin() as conn:
        conn.execute(
            text("UPDATE governance_crystals SET horizon_expires_at = :past WHERE crystal_id = :cid"),
            {"past": past, "cid": crystal_id},
        )
    before = _counter("crystal_horizon_strand_total")
    r = client.post(
        "/commit",
        headers=HEADERS,
        json={"crystal_id": crystal_id, "facets": facets, "committed_budget": "0"},
    )
    assert r.status_code == 409
    assert _counter("crystal_horizon_strand_total") == before + 1
