"""Security Enforcement Mesh — cross-platform runtime block tests."""
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


def _crystallize(client, *, platform: str, operation_id: str, facets: dict, policy_id: str, reserve: str = "0") -> str:
    r = client.post(
        "/crystallize",
        headers=HEADERS,
        json={
            "platform": platform,
            "operation_id": operation_id,
            "account_id": "tenant-default",
            "risk_tier": "critical",
            "facets": facets,
            "policy_id": policy_id,
            "reserved_budget": reserve,
        },
    )
    assert r.status_code == 200, r.text
    return r.json()["crystal_id"]


def test_mesh_blocks_egress_when_posture_drift(client):
    _crystallize(
        client,
        platform="posture_reconcile",
        operation_id="posture-1",
        policy_id="posture-high-us",
        facets={"asset_id": "srv-1", "match_state": "DRIFT", "critical_cves": 3, "patch_lag_days": 45},
    )
    egress_facets = {
        "flow_id": "flow-1",
        "destination_host": "api.openai.com",
        "egress_decision": "ALLOWED",
    }
    crystal_id = _crystallize(
        client,
        platform="egress_govern",
        operation_id="flow-1",
        policy_id="egress-critical-us",
        facets=egress_facets,
    )
    blocked = client.post(
        "/commit",
        headers=HEADERS,
        json={"crystal_id": crystal_id, "facets": egress_facets, "committed_budget": "0", "outcome": "allowed"},
    )
    assert blocked.status_code == 409
    assert "mesh block" in blocked.json()["detail"].lower()


def test_mesh_blocks_incident_when_threat_blocked(client):
    _crystallize(
        client,
        platform="threat_proxy",
        operation_id="threat-1",
        policy_id="threat-critical-us",
        facets={
            "request_id": "threat-1",
            "threat_score": "0.95",
            "threat_decision": "BLOCKED",
            "signals": "exfil_pattern",
        },
    )
    ir_facets = {
        "incident_id": "inc-1",
        "action_type": "isolate_host",
        "severity": "CRITICAL",
        "ir_decision": "AUTHORIZED",
        "approver": "soc-lead",
    }
    crystal_id = _crystallize(
        client,
        platform="incident_response_gate",
        operation_id="inc-1-isolate",
        policy_id="ir-critical-us",
        facets=ir_facets,
    )
    blocked = client.post(
        "/commit",
        headers=HEADERS,
        json={"crystal_id": crystal_id, "facets": ir_facets, "committed_budget": "0", "outcome": "authorized"},
    )
    assert blocked.status_code == 409


def test_mesh_blocks_egress_when_identity_violation(client):
    _crystallize(
        client,
        platform="identity_govern",
        operation_id="id-viol-1",
        policy_id="identity-high-us",
        facets={
            "principal": "cluster.local/ns/other/sa/evil",
            "workload_sa": "ig-platform-workload",
            "identity_decision": "VIOLATION",
        },
    )
    egress_facets = {
        "flow_id": "flow-2",
        "destination_host": "api.anthropic.com",
        "egress_decision": "ALLOWED",
    }
    crystal_id = _crystallize(
        client,
        platform="egress_govern",
        operation_id="flow-2",
        policy_id="egress-critical-us",
        facets=egress_facets,
    )
    blocked = client.post(
        "/commit",
        headers=HEADERS,
        json={"crystal_id": crystal_id, "facets": egress_facets, "committed_budget": "0", "outcome": "allowed"},
    )
    assert blocked.status_code == 409
