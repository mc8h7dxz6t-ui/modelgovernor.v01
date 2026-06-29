"""Cyber platform wedge unit tests — standalone mode."""
from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def _standalone():
    os.environ["CG_SPINE_ENABLED"] = "false"
    yield


def test_egress_govern_denies_unknown_host():
    from platforms.egress_govern.main import app

    client = TestClient(app)
    r = client.post(
        "/egress/evaluate",
        json={"flow_id": "f1", "destination_host": "evil.example.com"},
    )
    assert r.status_code == 403


def test_egress_govern_allows_listed_host():
    from platforms.egress_govern.main import app

    client = TestClient(app)
    r = client.post(
        "/egress/evaluate",
        json={"flow_id": "f2", "destination_host": "api.openai.com"},
    )
    assert r.status_code == 200
    assert r.json()["decision"] == "ALLOWED"


def test_threat_proxy_blocks_high_score():
    from platforms.threat_proxy.main import app

    client = TestClient(app)
    r = client.post(
        "/threat/score",
        json={
            "request_id": "r1",
            "payload_entropy": 0.9,
            "anomaly_signals": ["exfil_pattern", "tool_abuse"],
            "data_class": "secret",
        },
    )
    assert r.status_code == 403


def test_identity_govern_verifies_matching_principal():
    from platforms.identity_govern.main import app

    client = TestClient(app)
    r = client.post(
        "/identity/verify",
        json={
            "principal": "cluster.local/ns/cg/sa/ig-platform-workload",
            "workload_sa": "ig-platform-workload",
            "role_set": ["viewer"],
        },
    )
    assert r.status_code == 200
    assert r.json()["decision"] == "VERIFIED"


def test_posture_reconcile_flags_drift():
    from platforms.posture_reconcile.main import app

    client = TestClient(app)
    r = client.post(
        "/posture/ingest",
        json={"asset_id": "host-1", "critical_cves": 2, "patch_lag_days": 60},
    )
    assert r.status_code == 422
    assert r.json()["detail"]["match_state"] == "DRIFT"


def test_compliance_logger_seals_event():
    from platforms.compliance_logger.main import app

    client = TestClient(app)
    r = client.post(
        "/compliance/log",
        json={"framework": "SOC2", "control_id": "CC7.2", "evidence": {"event": "chain_verify"}},
    )
    assert r.status_code == 200
    assert len(r.json()["evidence_hash"]) == 64
