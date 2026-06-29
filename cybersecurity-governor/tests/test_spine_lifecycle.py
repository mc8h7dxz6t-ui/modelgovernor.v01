"""Spine lifecycle: crystallize → commit."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
SIDECAR = ROOT / "spine" / "sidecar"
sys.path.insert(0, str(SIDECAR))

from tests.conftest_spine import spine_db  # noqa: F401
from support.cyber_fixtures import EGRESS_PLATFORM, EGRESS_POLICY, egress_facets

HEADERS = {"x-internal-token": "test-token"}


@pytest.fixture()
def client(spine_db):
    from app.main import app

    return TestClient(app)


def test_crystallize_and_commit(client):
    facets = egress_facets(flow_id="clm-1")
    r = client.post(
        "/crystallize",
        headers=HEADERS,
        json={
            "platform": EGRESS_PLATFORM,
            "operation_id": "clm-1",
            "account_id": "tenant-default",
            "risk_tier": "high",
            "facets": facets,
            "policy_id": EGRESS_POLICY,
            "reserved_budget": "0",
        },
    )
    assert r.status_code == 200, r.text
    crystal_id = r.json()["crystal_id"]

    c = client.post(
        "/commit",
        headers=HEADERS,
        json={
            "crystal_id": crystal_id,
            "facets": facets,
            "committed_budget": "0",
            "outcome": "allowed",
        },
    )
    assert c.status_code == 200, c.text
    assert c.json()["status"] == "COMMITTED"

    recon = client.get(f"/internal/crystals/{crystal_id}/reconstruct", headers=HEADERS)
    assert recon.status_code == 200
    body = recon.json()
    assert body["crystal"]["terminal_state"] == "COMMITTED"
    assert len(body["events"]) >= 2


def test_fingerprint_mismatch_blocked(client):
    facets = egress_facets(flow_id="clm-2")
    r = client.post(
        "/crystallize",
        headers=HEADERS,
        json={
            "platform": EGRESS_PLATFORM,
            "operation_id": "clm-2",
            "risk_tier": "high",
            "facets": facets,
        },
    )
    crystal_id = r.json()["crystal_id"]
    bad = client.post(
        "/commit",
        headers=HEADERS,
        json={
            "crystal_id": crystal_id,
            "facets": egress_facets(flow_id="clm-2", host="evil.example.com", decision="DENIED"),
            "committed_budget": "0",
        },
    )
    assert bad.status_code == 409


def test_verify_chain_valid(client):
    facets = egress_facets(flow_id="clm-3")
    r = client.post(
        "/crystallize",
        headers=HEADERS,
        json={"platform": EGRESS_PLATFORM, "operation_id": "clm-3", "risk_tier": "standard", "facets": facets},
    )
    crystal_id = r.json()["crystal_id"]
    client.post(
        "/commit",
        headers=HEADERS,
        json={"crystal_id": crystal_id, "facets": facets, "committed_budget": "0", "outcome": "allowed"},
    )
    verify = client.get("/internal/security/verify-chain", headers=HEADERS)
    assert verify.status_code == 200
    assert verify.json()["valid"] is True


def test_diagnostic_mode_blocks_writes(client, monkeypatch):
    from app.diagnostic_mode import enter_diagnostic_mode

    enter_diagnostic_mode(component="test", reason="probe")
    r = client.post(
        "/crystallize",
        headers=HEADERS,
        json={"platform": EGRESS_PLATFORM, "operation_id": "clm-diag", "risk_tier": "high", "facets": {}},
    )
    assert r.status_code == 503
    from app.diagnostic_mode import clear_diagnostic_mode

    clear_diagnostic_mode()
