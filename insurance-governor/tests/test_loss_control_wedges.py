from decimal import Decimal

from platforms.indemnity_pay_gate.pay_gate import DEFAULT_GOLDEN_UK, evaluate_indemnity_payment
from platforms.model_risk_freeze.freeze_controller import (
    ModelRiskController,
    VersionRegistry,
    evaluate_inference,
)
from platforms.reserve_reconcile.reconcile_gate import evaluate_reserve_match
from platforms.underwriting_govern.fairness_gate import evaluate_underwriting_fairness


def test_indemnity_pay_gate_blocks_social_engineering():
    result = evaluate_indemnity_payment(
        payment_id="p1",
        payee_name="Acme Indemnity Trust",
        payee_account="US44ACME001",
        amount=Decimal("100000"),
        golden=DEFAULT_GOLDEN_UK,
        social_engineering_flag=True,
    )
    assert result.decision == "BLOCKED"


def test_model_risk_freeze_on_version_drift():
    reg = VersionRegistry(approved_version="v1.0")
    ctrl = ModelRiskController()
    result = evaluate_inference(
        inference_id="inf-1",
        runtime_version="v9.9",
        registry=reg,
        controller=ctrl,
        jurisdiction="UK",
    )
    assert result.freeze_state == "FROZEN"
    assert ctrl.state.value == "FROZEN"


def test_underwriting_govern_uk_violation():
    result = evaluate_underwriting_fairness(
        application_id="uk-app-1",
        score=0.7,
        protected_attribute_deltas={"postcode_sector": 0.22},
        jurisdiction="UK",
    )
    assert result.decision == "VIOLATION"
    assert result.adverse_action_required is True


def test_underwriting_govern_us_compliant():
    result = evaluate_underwriting_fairness(
        application_id="us-app-1",
        score=0.8,
        protected_attribute_deltas={"zip_code": 0.05},
        jurisdiction="US",
    )
    assert result.decision == "COMPLIANT"


def test_reserve_reconcile_drift():
    result = evaluate_reserve_match(
        claim_id="rc-1",
        case_reserve=Decimal("100000"),
        reinsurance_reserve=Decimal("80000"),
        jurisdiction="US",
    )
    assert result.match_state == "DRIFT"
    assert result.decision == "DRIFT"
