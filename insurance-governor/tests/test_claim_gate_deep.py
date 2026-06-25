from dataclasses import replace
from datetime import date
from decimal import Decimal

from platforms.claim_gate.payment_rail import PaymentStatus, reset_payment_store, submit_payment
from platforms.claim_gate.payout_gate import evaluate_payout
from platforms.claim_gate.policy_rules import DEFAULT_POLICIES, evaluate_policy_rules
from platforms.claim_gate.siu_workflow import evaluate_siu


def test_policy_deductible_and_auto_approve():
    policy = DEFAULT_POLICIES["POL-AUTO-001"]
    trace = evaluate_policy_rules(
        policy=policy,
        payout_amount=Decimal("10000.00"),
        loss_date=date(2025, 6, 1),
    )
    assert trace.passed is True
    assert trace.decision == "APPROVED"
    assert trace.net_payable == Decimal("9500.00")
    assert "deductible_applied" in trace.rules_applied


def test_policy_aggregate_exhausted():
    policy = DEFAULT_POLICIES["POL-AUTO-001"]
    exhausted = replace(policy, aggregate_used=Decimal("2000000.00"))
    trace = evaluate_policy_rules(
        policy=exhausted,
        payout_amount=Decimal("1000.00"),
        loss_date=date(2025, 6, 1),
    )
    assert trace.decision == "DECLINED"
    assert trace.reason == "aggregate_exhausted"


def test_siu_blocks_high_fraud_score():
    result = evaluate_payout(
        claim_id="fraud-1",
        payout_amount=Decimal("5000.00"),
        policy=DEFAULT_POLICIES["POL-AUTO-001"],
        fraud_signals=["staged_loss_pattern", "duplicate_claim"],
    )
    assert result.decision == "DECLINED"


def test_payment_rail_idempotent_and_requires_crystal():
    reset_payment_store()
    blocked = submit_payment(
        claim_id="c-pay-1",
        amount=Decimal("100.00"),
        currency="USD",
        payee_id="payee-1",
        idempotency_key="idem-1",
        gate_decision="HELD",
        crystal_id="crystal-1",
    )
    assert blocked.status == PaymentStatus.BLOCKED

    approved = submit_payment(
        claim_id="c-pay-2",
        amount=Decimal("100.00"),
        currency="USD",
        payee_id="payee-1",
        idempotency_key="idem-2",
        gate_decision="APPROVED",
        crystal_id="crystal-2",
    )
    assert approved.status == PaymentStatus.COMPLETED
    again = submit_payment(
        claim_id="c-pay-2",
        amount=Decimal("100.00"),
        currency="USD",
        payee_id="payee-1",
        idempotency_key="idem-2",
        gate_decision="APPROVED",
        crystal_id="crystal-2",
    )
    assert again.payment_id == approved.payment_id


def test_siu_referral_endpoint_logic():
    referral = evaluate_siu(claim_id="siu-1", signals=["late_reporting"], siu_flag=True)
    assert referral.state.value in ("REFERRED", "BLOCKED")
    assert referral.fraud_score > 0
