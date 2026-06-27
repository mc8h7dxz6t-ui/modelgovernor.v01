"""Claim chain anchor tests."""
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


def test_anchor_head_after_commit(client):
    facets = {"claim_id": "anchor-1", "payout_amount": "10.00"}
    r = client.post(
        "/crystallize",
        headers=HEADERS,
        json={"platform": "claim_gate", "operation_id": "anchor-1", "risk_tier": "standard", "facets": facets},
    )
    crystal_id = r.json()["crystal_id"]
    client.post(
        "/commit",
        headers=HEADERS,
        json={"crystal_id": crystal_id, "facets": facets, "committed_reserve": "0", "outcome": "closed"},
    )
    anchor = client.post("/internal/claims/anchor-head", headers=HEADERS)
    assert anchor.status_code == 200
    body = anchor.json()
    assert body["anchored"] is True
    assert body["head_hash"]

    anchor2 = client.post("/internal/claims/anchor-head", headers=HEADERS)
    assert anchor2.json()["anchored"] is False
