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
from support.cyber_fixtures import COMPLIANCE_PLATFORM, compliance_facets

HEADERS = {"x-internal-token": "test-token"}


@pytest.fixture()
def client(spine_db):
    from app.main import app

    return TestClient(app)


def test_regulatory_export_after_commit(client):
    facets = compliance_facets()
    cry = client.post(
        "/crystallize",
        headers=HEADERS,
        json={
            "platform": COMPLIANCE_PLATFORM,
            "operation_id": "reg-export-1",
            "risk_tier": "standard",
            "facets": facets,
        },
    )
    crystal_id = cry.json()["crystal_id"]
    client.post(
        "/commit",
        headers=HEADERS,
        json={"crystal_id": crystal_id, "facets": facets, "committed_budget": "0", "outcome": "logged"},
    )
    export = client.get("/internal/regulatory/export", headers=HEADERS)
    assert export.status_code == 200
    body = export.json()
    assert body["chain_verification"]["valid"] is True
    assert body["chain_head"]
    assert len(body["security_events"]) >= 1
    assert "exported_at" in body
