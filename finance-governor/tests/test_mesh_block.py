"""Crystal mesh cross-platform invariant."""
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


def test_mesh_blocks_wire_when_algo_frozen(client):
    freeze_facets = {"freeze_state": "FROZEN", "desk_id": "desk-1"}
    client.post(
        "/crystallize",
        headers=HEADERS,
        json={
            "platform": "algofreeze",
            "operation_id": "freeze-mesh-1",
            "risk_tier": "critical",
            "facets": freeze_facets,
        },
    )
    wire_facets = {"amount": "100.00", "currency": "USD"}
    wr = client.post(
        "/crystallize",
        headers=HEADERS,
        json={
            "platform": "wire_match",
            "operation_id": "wire-mesh-1",
            "risk_tier": "high",
            "facets": wire_facets,
        },
    )
    crystal_id = wr.json()["crystal_id"]
    blocked = client.post(
        "/commit",
        headers=HEADERS,
        json={"crystal_id": crystal_id, "facets": wire_facets, "committed_exposure": "0"},
    )
    assert blocked.status_code == 409
    assert "mesh block" in blocked.json()["detail"]
