"""Crystallize idempotency and fingerprint replay protection."""
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


def test_crystallize_replay_same_facets(client):
    facets = {"amount": "1000.00"}
    first = client.post(
        "/crystallize",
        headers=HEADERS,
        json={"platform": "wire_match", "operation_id": "idem-1", "risk_tier": "high", "facets": facets},
    )
    second = client.post(
        "/crystallize",
        headers=HEADERS,
        json={"platform": "wire_match", "operation_id": "idem-1", "risk_tier": "high", "facets": facets},
    )
    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["status"] == "REPLAY"
    assert second.json()["crystal_id"] == first.json()["crystal_id"]


def test_crystallize_replay_fingerprint_mismatch(client):
    client.post(
        "/crystallize",
        headers=HEADERS,
        json={"platform": "wire_match", "operation_id": "idem-2", "risk_tier": "high", "facets": {"amount": "1.00"}},
    )
    bad = client.post(
        "/crystallize",
        headers=HEADERS,
        json={"platform": "wire_match", "operation_id": "idem-2", "risk_tier": "high", "facets": {"amount": "9.00"}},
    )
    assert bad.status_code == 409
    assert "fingerprint mismatch" in bad.json()["detail"]
