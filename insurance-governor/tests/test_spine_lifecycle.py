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

HEADERS = {"x-internal-token": "test-token"}


@pytest.fixture()
def client(spine_db):
    from app.main import app

    return TestClient(app)


def test_crystallize_and_commit(client):
    facets = {"claim_id": "clm-1", "payout_amount": "50000.00", "currency": "USD"}
    r = client.post(
        "/crystallize",
        headers=HEADERS,
        json={
            "platform": "claim_gate",
            "operation_id": "clm-1",
            "account_id": "carrier-default",
            "risk_tier": "high",
            "facets": facets,
            "policy_id": "claim-high-us",
            "reserved_reserve": "50000.00",
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
            "committed_reserve": "50000.00",
            "outcome": "paid",
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
    facets = {"claim_id": "clm-2", "payout_amount": "100.00"}
    r = client.post(
        "/crystallize",
        headers=HEADERS,
        json={
            "platform": "claim_gate",
            "operation_id": "clm-2",
            "risk_tier": "high",
            "facets": facets,
        },
    )
    crystal_id = r.json()["crystal_id"]
    bad = client.post(
        "/commit",
        headers=HEADERS,
        json={"crystal_id": crystal_id, "facets": {"claim_id": "clm-2", "payout_amount": "9000000.00"}, "committed_reserve": "0"},
    )
    assert bad.status_code == 409


def test_verify_chain_valid(client):
    facets = {"claim_id": "clm-3", "payout_amount": "10.00"}
    r = client.post(
        "/crystallize",
        headers=HEADERS,
        json={"platform": "claim_gate", "operation_id": "clm-3", "risk_tier": "standard", "facets": facets},
    )
    crystal_id = r.json()["crystal_id"]
    client.post(
        "/commit",
        headers=HEADERS,
        json={"crystal_id": crystal_id, "facets": facets, "committed_reserve": "0", "outcome": "closed"},
    )
    verify = client.get("/internal/claims/verify-chain", headers=HEADERS)
    assert verify.status_code == 200
    assert verify.json()["valid"] is True


def test_diagnostic_mode_blocks_writes(client, monkeypatch):
    from app.diagnostic_mode import enter_diagnostic_mode

    enter_diagnostic_mode(component="test", reason="probe")
    r = client.post(
        "/crystallize",
        headers=HEADERS,
        json={"platform": "claim_gate", "operation_id": "clm-diag", "risk_tier": "high", "facets": {}},
    )
    assert r.status_code == 503
