"""ClaimGate payout evaluation — composes policy rules + SIU workflow."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from platforms.common.crystal import canonical_fingerprint

from .policy_rules import PolicyContext, PolicyEvaluationTrace, evaluate_policy_rules
from .siu_workflow import SiuReferral, SiuState, evaluate_siu


@dataclass(frozen=True)
class PayoutEvaluation:
    approved: bool
    decision: str
    reason: str | None
    score: float
    net_payable: Decimal
    policy_trace: PolicyEvaluationTrace | None = None
    siu_referral: SiuReferral | None = None


def evaluate_payout(
    *,
    claim_id: str,
    payout_amount: Decimal,
    policy: PolicyContext | None = None,
    policy_limit: Decimal | None = None,
    auto_approve_limit: Decimal | None = None,
    loss_date: date | None = None,
    siu_flag: bool = False,
    fraud_signals: list[str] | None = None,
) -> PayoutEvaluation:
    signals = list(fraud_signals or [])
    siu = evaluate_siu(claim_id=claim_id, signals=signals, siu_flag=siu_flag)

    if siu.state in (SiuState.REFERRED, SiuState.BLOCKED):
        return PayoutEvaluation(
            approved=False,
            decision="REFERRED" if siu.state == SiuState.REFERRED else "DECLINED",
            reason=f"siu_{siu.state.value.lower()}",
            score=siu.fraud_score,
            net_payable=Decimal("0"),
            siu_referral=siu,
        )

    if policy is not None:
        trace = evaluate_policy_rules(
            policy=policy,
            payout_amount=payout_amount,
            loss_date=loss_date or date.today(),
            siu_flag=siu_flag,
            fraud_signals=signals,
        )
        return PayoutEvaluation(
            approved=trace.passed,
            decision=trace.decision,
            reason=trace.reason,
            score=trace.score,
            net_payable=trace.net_payable,
            policy_trace=trace,
            siu_referral=siu,
        )

    # Legacy simple path
    limit = policy_limit or Decimal("5000000.00")
    auto = auto_approve_limit or Decimal("250000.00")
    if payout_amount > limit:
        return PayoutEvaluation(False, "HELD", "exceeds_policy_limit", 0.0, Decimal("0"), siu_referral=siu)
    if payout_amount > auto:
        return PayoutEvaluation(False, "HELD", "above_auto_approve_threshold", 0.5, payout_amount, siu_referral=siu)
    return PayoutEvaluation(True, "APPROVED", None, 1.0, payout_amount, siu_referral=siu)


def payout_facets(
    *,
    claim_id: str,
    payout_amount: Decimal,
    currency: str,
    decision: str,
    score: float,
    net_payable: Decimal | None = None,
    policy_number: str | None = None,
    siu_referral_id: str | None = None,
    payment_id: str | None = None,
    vendor: str | None = None,
) -> dict:
    amount = str(payout_amount)
    net = str(net_payable if net_payable is not None else payout_amount)
    facets: dict = {
        "claim_id": claim_id,
        "payout_amount": amount,
        "net_payable": net,
        "currency": currency,
        "gate_decision": decision,
        "gate_score": score,
        "claim_fingerprint": canonical_fingerprint("claim_gate", claim_id, {"amount": net, "currency": currency}),
    }
    if policy_number:
        facets["policy_number"] = policy_number
    if siu_referral_id:
        facets["siu_referral_id"] = siu_referral_id
    if payment_id:
        facets["payment_id"] = payment_id
    if vendor:
        facets["fnol_vendor"] = vendor
    return facets
