"""Security chain verify and anchor lifecycle."""
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


def test_verify_chain_empty_valid(client):
    r = client.get("/internal/security/verify-chain", headers=HEADERS)
    assert r.status_code == 200
    assert r.json()["valid"] is True


def test_anchor_head_after_crystallize(client):
    facets = {"session_state": "AUTHORIZED"}
    cr = client.post(
        "/crystallize",
        headers=HEADERS,
        json={
            "platform": "identity_gate",
            "operation_id": "anchor-test-1",
            "risk_tier": "critical",
            "facets": facets,
        },
    )
    crystal_id = cr.json()["crystal_id"]
    client.post(
        "/commit",
        headers=HEADERS,
        json={"crystal_id": crystal_id, "facets": facets, "outcome": "authorized"},
    )
    verify = client.get("/internal/security/verify-chain", headers=HEADERS)
    assert verify.json()["sealed_count"] >= 2

    anchor = client.post("/internal/security/anchor-head", headers=HEADERS)
    assert anchor.status_code == 200
    body = anchor.json()
    assert body["anchored"] is True
    assert body["head_hash"] is not None


def test_lineage_ingest_persists(client):
    r = client.post(
        "/internal/lineage/ingest",
        headers=HEADERS,
        json={
            "source": "falco",
            "payload": {
                "rule": "Terminal shell in container",
                "priority": "Critical",
                "time": "2026-06-26T12:00:00Z",
                "output_fields": {"proc.name": "bash", "proc.pname": "sh", "user.name": "root"},
            },
        },
    )
    assert r.status_code == 200
    assert r.json()["edge_type"] == "process_exec"

    dag = client.get("/internal/lineage/dag/root", headers=HEADERS)
    assert dag.status_code == 200
    assert len(dag.json()) >= 1
