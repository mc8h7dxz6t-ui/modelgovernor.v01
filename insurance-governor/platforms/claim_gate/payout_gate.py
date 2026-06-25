"""ClaimGate payout evaluation gate."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from platforms.common.crystal import canonical_fingerprint


@dataclass(frozen=True)
class PayoutEvaluation:
    approved: bool
    decision: str
    reason: str | None
    score: float


def evaluate_payout(
    *,
    claim_id: str,
    payout_amount: Decimal,
    policy_limit: Decimal,
    auto_approve_limit: Decimal,
    siu_flag: bool = False,
) -> PayoutEvaluation:
    if siu_flag:
        return PayoutEvaluation(approved=False, decision="REFERRED", reason="siu_review_required", score=0.0)
    if payout_amount > policy_limit:
        return PayoutEvaluation(approved=False, decision="HELD", reason="exceeds_policy_limit", score=0.0)
    if payout_amount > auto_approve_limit:
        return PayoutEvaluation(approved=False, decision="HELD", reason="above_auto_approve_threshold", score=0.5)
    return PayoutEvaluation(approved=True, decision="APPROVED", reason=None, score=1.0)


def payout_facets(*, claim_id: str, payout_amount: Decimal, currency: str, decision: str, score: float) -> dict:
    amount = str(payout_amount)
    return {
        "claim_id": claim_id,
        "payout_amount": amount,
        "currency": currency,
        "gate_decision": decision,
        "gate_score": score,
        "claim_fingerprint": canonical_fingerprint("claim_gate", claim_id, {"amount": amount, "currency": currency}),
    }
