"""Per-wedge invariant counter tests — zero error budget signals."""
from __future__ import annotations

from decimal import Decimal

from fastapi.testclient import TestClient

from platforms.common.platform_metrics import get_platform_counters
from platforms.indemnity_pay_gate.main import app as indemnity_app
from platforms.indemnity_pay_gate.pay_gate import DEFAULT_GOLDEN_UK, evaluate_indemnity_payment
from platforms.model_risk_freeze.freeze_controller import (
    ModelRiskController,
    VersionRegistry,
    evaluate_inference,
)
from platforms.model_risk_freeze.main import app as freeze_app


def _reset(platform: str) -> None:
    counters = get_platform_counters(platform)
    with counters._lock:
        for key in counters._counters:
            counters._counters[key] = 0


def test_model_risk_freeze_version_mismatch_increments_counter():
    _reset("model_risk_freeze")
    client = TestClient(freeze_app)
    response = client.post(
        "/inference/evaluate",
        json={
            "inference_id": "inv-counter-1",
            "runtime_version": "rogue-v9",
            "jurisdiction": "US",
        },
    )
    assert response.status_code == 403
    snap = get_platform_counters("model_risk_freeze").snapshot()
    assert snap["version_mismatch_freeze_total"] >= 1


def test_model_risk_freeze_allowed_increments_counter():
    _reset("model_risk_freeze")
    client = TestClient(freeze_app)
    response = client.post(
        "/inference/evaluate",
        json={
            "inference_id": "inv-counter-2",
            "runtime_version": "claims-model-uk-v2.1.0",
            "jurisdiction": "UK",
        },
    )
    assert response.status_code == 200
    snap = get_platform_counters("model_risk_freeze").snapshot()
    assert snap["inference_allowed_total"] >= 1


def test_indemnity_pay_gate_social_engineering_counter():
    _reset("indemnity_pay_gate")
    client = TestClient(indemnity_app)
    response = client.post(
        "/indemnity/evaluate",
        json={
            "payment_id": "pay-counter-1",
            "payee_name": "Acme Indemnity Trust",
            "payee_account": "US44ACME001",
            "amount": "100000.00",
            "jurisdiction": "US",
            "social_engineering_flag": True,
        },
    )
    assert response.status_code == 200
    assert response.json()["decision"] == "BLOCKED"
    snap = get_platform_counters("indemnity_pay_gate").snapshot()
    assert snap["indemnity_social_engineering_blocked_total"] >= 1


def test_indemnity_pay_gate_held_and_approved_counters():
    _reset("indemnity_pay_gate")
    client = TestClient(indemnity_app)
    held = client.post(
        "/indemnity/evaluate",
        json={
            "payment_id": "pay-counter-2",
            "payee_name": "Totally Wrong Payee LLC",
            "payee_account": "US44ACME001",
            "amount": "100000.00",
            "jurisdiction": "US",
        },
    )
    assert held.json()["decision"] == "HELD"
    approved = client.post(
        "/indemnity/evaluate",
        json={
            "payment_id": "pay-counter-3",
            "payee_name": "Acme Indemnity Trust",
            "payee_account": "US44ACME001",
            "amount": "100000.00",
            "jurisdiction": "US",
        },
    )
    assert approved.json()["decision"] == "APPROVED"
    snap = get_platform_counters("indemnity_pay_gate").snapshot()
    assert snap["indemnity_payee_held_total"] >= 1
    assert snap["indemnity_payee_approved_total"] >= 1


def test_indemnity_fat_finger_counter_via_gate():
    _reset("indemnity_pay_gate")
    result = evaluate_indemnity_payment(
        payment_id="ff-1",
        payee_name="Acme Indemnity Trust",
        payee_account="US44ACME001",
        amount=Decimal("99999999"),
        golden=DEFAULT_GOLDEN_UK,
    )
    assert result.decision == "HELD"
    assert result.reason == "amount_anomaly_fat_finger"
