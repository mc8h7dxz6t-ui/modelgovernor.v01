"""Security chain anchor tests."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

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


def test_anchor_head_after_commit(client):
    facets = egress_facets(flow_id="anchor-1")
    r = client.post(
        "/crystallize",
        headers=HEADERS,
        json={"platform": EGRESS_PLATFORM, "operation_id": "anchor-1", "risk_tier": "standard", "facets": facets},
    )
    crystal_id = r.json()["crystal_id"]
    client.post(
        "/commit",
        headers=HEADERS,
        json={"crystal_id": crystal_id, "facets": facets, "committed_budget": "0", "outcome": "allowed"},
    )
    anchor = client.post("/internal/security/anchor-head", headers=HEADERS)
    assert anchor.status_code == 200
    body = anchor.json()
    assert body["anchored"] is True
    assert body["head_hash"]

    anchor2 = client.post("/internal/security/anchor-head", headers=HEADERS)
    assert anchor2.json()["anchored"] is False
