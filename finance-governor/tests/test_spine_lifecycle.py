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
    facets = {"amount": "7800000.00", "currency": "USD", "beneficiary_hash": "abc"}
    r = client.post(
        "/crystallize",
        headers=HEADERS,
        json={
            "platform": "wire_match",
            "operation_id": "wire-test-1",
            "account_id": "desk-default",
            "risk_tier": "high",
            "facets": facets,
            "policy_id": "wire-critical-us",
            "reserved_exposure": "1000.00",
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
            "committed_exposure": "1000.00",
            "outcome": "sent",
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
    facets = {"amount": "100.00"}
    r = client.post(
        "/crystallize",
        headers=HEADERS,
        json={
            "platform": "wire_match",
            "operation_id": "wire-test-2",
            "risk_tier": "high",
            "facets": facets,
        },
    )
    crystal_id = r.json()["crystal_id"]
    bad = client.post(
        "/commit",
        headers=HEADERS,
        json={"crystal_id": crystal_id, "facets": {"amount": "900000000.00"}, "committed_exposure": "0"},
    )
    assert bad.status_code == 409
