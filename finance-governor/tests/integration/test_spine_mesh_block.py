"""Mesh block integration — algo FROZEN blocks wire commit."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
SIDECAR = ROOT / "spine" / "sidecar"
sys.path.insert(0, str(SIDECAR))

FG_TESTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(FG_TESTS))

from conftest_spine import spine_db  # noqa: F401

HEADERS = {"x-internal-token": "test-token"}


@pytest.fixture()
def client(spine_db):
    from app.main import app

    return TestClient(app)


def test_mesh_blocks_wire_commit_when_algo_frozen(client):
    client.post(
        "/crystallize",
        headers=HEADERS,
        json={
            "platform": "algofreeze",
            "operation_id": "freeze-mesh-1",
            "risk_tier": "critical",
            "facets": {"freeze_state": "FROZEN", "reason": "FEED_DEGRADED"},
        },
    )
    wr = client.post(
        "/crystallize",
        headers=HEADERS,
        json={
            "platform": "wire_match",
            "operation_id": "wire-mesh-1",
            "risk_tier": "high",
            "facets": {"amount": "7800000.00"},
        },
    )
    crystal_id = wr.json()["crystal_id"]
    blocked = client.post(
        "/commit",
        headers=HEADERS,
        json={
            "crystal_id": crystal_id,
            "facets": {"amount": "7800000.00"},
            "committed_exposure": "7800000.00",
        },
    )
    assert blocked.status_code == 409
