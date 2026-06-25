"""CreditGovern platform tests."""
import sys
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from platforms.common.mesh_guard import DeskState, get_mesh_guard
from platforms.credit_govern.exposure_ledger import ExposureLedger
from platforms.credit_govern.main import app
from platforms.credit_govern.score_gate import PolicyRegistry, ScoreGate


@pytest.fixture()
def client():
    return TestClient(app)


def _payload(app_id: str = "app-1", amount: str = "5000.00", model: str = "credit-v3.2.1"):
    return {
        "application_id": app_id,
        "desk_id": "desk-consumer",
        "exposure_amount": amount,
        "model_version": model,
        "feature_snapshot_hash": "features-abc123",
    }


def test_reserve_before_score_approve(client):
    r = client.post("/governed/decision", json=_payload())
    assert r.status_code == 200
    body = r.json()
    assert body["status"] in ("SETTLED", "APPROVAL_REQUIRED", "STRANDED", "DENIED")


def test_model_version_mismatch_blocked(client):
    r = client.post("/governed/decision", json=_payload(model="shadow-v9"))
    assert r.json()["status"] == "BLOCKED"
    assert r.json()["reason"] == "MODEL_VERSION_MISMATCH"


def test_exposure_cap_enforcement():
    ledger = ExposureLedger()
    ledger.ensure_desk("d1", Decimal("1000"))
    gate = ScoreGate(
        ledger,
        PolicyRegistry(approved_model_version="v1", max_auto_approve_amount=Decimal("50000")),
    )
    result = gate.governed_decision(
        application_id="x1",
        desk_id="d1",
        exposure_amount=Decimal("2000"),
        model_version="v1",
        feature_snapshot_hash="hash-low-risk",
    )
    assert result["status"] == "DENIED"
    assert result["reason"] == "INSUFFICIENT_EXPOSURE"


def test_mesh_block_when_algo_frozen(client):
    mesh = get_mesh_guard()
    mesh.set_algo_frozen("VERSION_MISMATCH")
    try:
        r = client.post("/governed/decision", json=_payload(app_id="mesh-1"))
        assert r.json()["status"] == "BLOCKED"
        assert "MESH_BLOCK" in r.json()["reason"]
    finally:
        mesh.set_algo_active()


def test_auto_approve_threshold(client):
    r = client.post("/governed/decision", json=_payload(app_id="big-loan", amount="50000.00"))
    assert r.json()["status"] == "APPROVAL_REQUIRED"
