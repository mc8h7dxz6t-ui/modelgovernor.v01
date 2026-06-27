"""L4 runtime enforcement — behaviors pytest proves at commit time (not artifact presence)."""
from __future__ import annotations

import os
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
def spine_client(spine_db):
    from app.main import app

    return TestClient(app)


@pytest.fixture(autouse=True)
def _standalone_platforms():
    os.environ["CG_SPINE_ENABLED"] = "false"
    yield


def test_envoy_ext_authz_allows_allowlisted_host():
    from platforms.egress_govern.main import app

    client = TestClient(app)
    payload = {
        "attributes": {
            "request": {
                "http": {
                    "id": "envoy-flow-1",
                    "host": "api.openai.com",
                    "path": "/v1/chat/completions",
                    "headers": {":authority": "api.openai.com"},
                }
            }
        }
    }
    r = client.post("/envoy/authz/check", json=payload)
    assert r.status_code == 200
    assert r.json()["decision"] == "ALLOWED"


def test_envoy_ext_authz_denies_off_allowlist_host():
    from platforms.egress_govern.main import app

    client = TestClient(app)
    payload = {
        "attributes": {
            "request": {
                "http": {
                    "id": "envoy-flow-2",
                    "host": "evil-exfil.example",
                    "path": "/upload",
                }
            }
        }
    }
    r = client.post("/envoy/authz/check", json=payload)
    assert r.status_code == 403
    assert r.json()["detail"]["decision"] == "DENIED"


def test_mesh_blocks_egress_commit_after_identity_violation(spine_client):
    spine_client.post(
        "/crystallize",
        headers=HEADERS,
        json={
            "platform": "identity_govern",
            "operation_id": "rt-id-viol-1",
            "account_id": "tenant-default",
            "risk_tier": "critical",
            "facets": {
                "principal": "cluster.local/ns/other/sa/evil",
                "workload_sa": "ig-platform-workload",
                "identity_decision": "VIOLATION",
            },
            "policy_id": "identity-high-us",
            "reserved_budget": "0",
        },
    )
    egress_facets = {
        "flow_id": "rt-flow-1",
        "destination_host": "api.anthropic.com",
        "egress_decision": "ALLOWED",
    }
    crystal = spine_client.post(
        "/crystallize",
        headers=HEADERS,
        json={
            "platform": "egress_govern",
            "operation_id": "rt-flow-1",
            "account_id": "tenant-default",
            "risk_tier": "critical",
            "facets": egress_facets,
            "policy_id": "egress-critical-us",
            "reserved_budget": "0",
        },
    )
    assert crystal.status_code == 200
    blocked = spine_client.post(
        "/commit",
        headers=HEADERS,
        json={
            "crystal_id": crystal.json()["crystal_id"],
            "facets": egress_facets,
            "committed_budget": "0",
            "outcome": "allowed",
        },
    )
    assert blocked.status_code == 409
    assert "mesh block" in blocked.json()["detail"].lower()


def test_verify_chain_endpoint_reports_valid(spine_client):
    egress_facets = {
        "flow_id": "chain-1",
        "destination_host": "api.openai.com",
        "egress_decision": "ALLOWED",
    }
    crystal = spine_client.post(
        "/crystallize",
        headers=HEADERS,
        json={
            "platform": "egress_govern",
            "operation_id": "chain-1",
            "account_id": "tenant-default",
            "risk_tier": "critical",
            "facets": egress_facets,
            "policy_id": "egress-critical-us",
            "reserved_budget": "0",
        },
    )
    assert crystal.status_code == 200
    commit = spine_client.post(
        "/commit",
        headers=HEADERS,
        json={
            "crystal_id": crystal.json()["crystal_id"],
            "facets": egress_facets,
            "committed_budget": "0",
            "outcome": "allowed",
        },
    )
    assert commit.status_code == 200
    verify = spine_client.get("/internal/security/verify-chain", headers=HEADERS)
    assert verify.status_code == 200
    assert verify.json().get("valid") is True
