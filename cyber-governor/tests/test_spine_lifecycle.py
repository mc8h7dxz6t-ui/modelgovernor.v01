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
    facets = {
        "user_id": "alice@corp.example",
        "device_fingerprint": "dev_fp_trusted_workstation",
        "session_state": "AUTHORIZED",
    }
    r = client.post(
        "/crystallize",
        headers=HEADERS,
        json={
            "platform": "identity_gate",
            "operation_id": "session-test-1",
            "account_id": "tenant-default",
            "risk_tier": "critical",
            "facets": facets,
            "policy_id": "identity-critical-us",
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
            "committed_exposure": "0",
            "outcome": "authorized",
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
    facets = {"session_state": "AUTHORIZED"}
    r = client.post(
        "/crystallize",
        headers=HEADERS,
        json={
            "platform": "identity_gate",
            "operation_id": "session-test-2",
            "risk_tier": "critical",
            "facets": facets,
        },
    )
    crystal_id = r.json()["crystal_id"]
    bad = client.post(
        "/commit",
        headers=HEADERS,
        json={"crystal_id": crystal_id, "facets": {"session_state": "STRANDED"}, "committed_exposure": "0"},
    )
    assert bad.status_code == 409
