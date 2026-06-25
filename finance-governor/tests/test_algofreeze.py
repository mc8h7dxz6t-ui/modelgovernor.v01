"""AlgoFreeze platform tests."""
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from platforms.algofreeze.main import app


@pytest.fixture()
def client():
    import platforms.algofreeze.main as main_mod
    from platforms.algofreeze.deploy_registry import DeployRegistry
    from platforms.algofreeze.metrics_hooks import record_unfreeze

    record_unfreeze(main_mod._controller)
    main_mod._registry = DeployRegistry()
    main_mod._registry.register_approval("approved-sha-v1", approved_by="test", ci_pipeline_id="test")
    return TestClient(app)


def test_order_routes_when_active(client):
    r = client.post("/orders", json={"order_id": "o1", "runtime_sha": "approved-sha-v1"})
    assert r.status_code == 200
    assert r.json()["status"] == "ROUTED"


def test_version_mismatch_freezes_and_blocks(client):
    bad = client.post("/orders", json={"order_id": "o2", "runtime_sha": "wrong-sha"})
    assert bad.status_code == 403
    assert "VERSION_MISMATCH" in bad.json()["detail"]
    blocked = client.post("/orders", json={"order_id": "o3", "runtime_sha": "approved-sha-v1"})
    assert blocked.status_code == 403
    assert "FROZEN" in blocked.json()["detail"]
    assert client.get("/status").json()["freeze_state"] == "FROZEN"


def test_no_egress_when_frozen(client):
    client.post("/orders", json={"order_id": "o4", "runtime_sha": "bad"})
    status = client.get("/status").json()
    assert status["blocked_egress_attempts"] >= 1


def test_deploy_registry_ci_approval(client):
    r = client.post(
        "/admin/deploy-registry",
        json={"sha": "approved-sha-v2", "approved_by": "ci-github-actions", "ci_pipeline_id": "run-99"},
    )
    assert r.json()["approved_sha"] == "approved-sha-v2"
    ok = client.post("/orders", json={"order_id": "o5", "runtime_sha": "approved-sha-v2"})
    assert ok.status_code == 200


def test_metrics_endpoint(client):
    r = client.get("/metrics")
    assert r.status_code == 200
    assert "frozen_egress_blocked_total" in r.text
    assert "frozen_egress_violation_total" in r.text
