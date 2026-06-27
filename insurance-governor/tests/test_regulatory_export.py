"""Regulatory export API — examiner bundle."""
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


def test_regulatory_export_after_commit(client):
    facets = {"claim_id": "reg-export-1", "payout_amount": "100.00"}
    cry = client.post(
        "/crystallize",
        headers=HEADERS,
        json={
            "platform": "claim_gate",
            "operation_id": "reg-export-1",
            "risk_tier": "standard",
            "facets": facets,
        },
    )
    crystal_id = cry.json()["crystal_id"]
    client.post(
        "/commit",
        headers=HEADERS,
        json={"crystal_id": crystal_id, "facets": facets, "committed_reserve": "0", "outcome": "closed"},
    )
    export = client.get("/internal/regulatory/export", headers=HEADERS)
    assert export.status_code == 200
    body = export.json()
    assert body["chain_verification"]["valid"] is True
    assert body["chain_head"]
    assert len(body["claim_events"]) >= 1
    assert "exported_at" in body
