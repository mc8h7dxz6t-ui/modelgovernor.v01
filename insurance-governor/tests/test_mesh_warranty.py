"""Warranty Enforcement Engine — mesh block integration tests."""
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


def _crystallize(client, *, platform: str, operation_id: str, facets: dict, reserve: str = "0") -> str:
    r = client.post(
        "/crystallize",
        headers=HEADERS,
        json={
            "platform": platform,
            "operation_id": operation_id,
            "account_id": "carrier-default",
            "risk_tier": "critical",
            "facets": facets,
            "policy_id": "claim-high-us",
            "reserved_reserve": reserve,
        },
    )
    assert r.status_code == 200, r.text
    return r.json()["crystal_id"]


def test_mesh_blocks_claim_payout_when_model_frozen(client):
    _crystallize(
        client,
        platform="model_risk_freeze",
        operation_id="freeze-1",
        facets={"inference_id": "freeze-1", "freeze_state": "FROZEN", "model_version": "bad-v1"},
    )
    claim_facets = {
        "claim_id": "mesh-clm-1",
        "payout_amount": "1000.00",
        "net_payable": "1000.00",
        "currency": "USD",
        "gate_decision": "APPROVED",
        "gate_score": 1.0,
    }
    crystal_id = _crystallize(client, platform="claim_gate", operation_id="mesh-clm-1", facets=claim_facets, reserve="1000.00")
    blocked = client.post(
        "/commit",
        headers=HEADERS,
        json={"crystal_id": crystal_id, "facets": claim_facets, "committed_reserve": "1000.00", "outcome": "paid"},
    )
    assert blocked.status_code == 409
    assert "mesh block" in blocked.json()["detail"].lower()


def test_mesh_blocks_indemnity_when_claim_referred(client):
    referred_facets = {
        "claim_id": "mesh-clm-2",
        "payout_amount": "5000.00",
        "net_payable": "0",
        "currency": "USD",
        "gate_decision": "REFERRED",
        "gate_score": 0.4,
    }
    _crystallize(client, platform="claim_gate", operation_id="mesh-clm-2", facets=referred_facets)

    pay_facets = {
        "payment_id": "pay-mesh-1",
        "payee_hash": "GB29LOYD1234",
        "semantic_score": 0.95,
        "indemnity_decision": "APPROVED",
        "jurisdiction": "UK",
        "currency": "GBP",
    }
    crystal_id = _crystallize(
        client,
        platform="indemnity_pay_gate",
        operation_id="pay-mesh-1",
        facets=pay_facets,
        reserve="5000.00",
    )
    blocked = client.post(
        "/commit",
        headers=HEADERS,
        json={"crystal_id": crystal_id, "facets": pay_facets, "committed_reserve": "5000.00", "outcome": "indemnity_paid"},
    )
    assert blocked.status_code == 409


def test_mesh_blocks_bind_when_underwriting_violation(client):
    _crystallize(
        client,
        platform="underwriting_govern",
        operation_id="uw-viol-1",
        facets={
            "application_id": "uw-viol-1",
            "govern_decision": "VIOLATION",
            "bias_score": 0.42,
            "jurisdiction": "US",
        },
    )
    bind_facets = {"application_id": "uw-viol-1", "premium": "10000", "limit": "500000"}
    crystal_id = _crystallize(
        client,
        platform="bind_authority",
        operation_id="bind-uw-viol-1",
        facets=bind_facets,
        reserve="10000.00",
    )
    blocked = client.post(
        "/commit",
        headers=HEADERS,
        json={"crystal_id": crystal_id, "facets": bind_facets, "committed_reserve": "10000.00", "outcome": "bound"},
    )
    assert blocked.status_code == 409
