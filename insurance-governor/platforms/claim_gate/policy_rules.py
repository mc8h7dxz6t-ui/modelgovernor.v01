"""Carrier policy rule engine for ClaimGate — coverage, limits, deductibles, jurisdiction."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from enum import Enum


class CoverageLine(str, Enum):
    AUTO_LIABILITY = "auto_liability"
    PROPERTY = "property"
    GENERAL_LIABILITY = "general_liability"
    WORKERS_COMP = "workers_comp"


@dataclass(frozen=True)
class PolicyContext:
    policy_number: str
    coverage_line: CoverageLine
    per_occurrence_limit: Decimal
    aggregate_limit: Decimal
    aggregate_used: Decimal
    deductible: Decimal
    auto_approve_limit: Decimal
    effective_date: date
    expiration_date: date
    jurisdiction: str = "US"
    coverage_active: bool = True
    regulatory_hold: bool = False


@dataclass
class PolicyEvaluationTrace:
    passed: bool
    decision: str
    reason: str | None
    score: float
    net_payable: Decimal
    rules_applied: list[str] = field(default_factory=list)


def evaluate_policy_rules(
    *,
    policy: PolicyContext,
    payout_amount: Decimal,
    loss_date: date,
    siu_flag: bool = False,
    fraud_signals: list[str] | None = None,
) -> PolicyEvaluationTrace:
    trace: list[str] = []
    fraud_signals = fraud_signals or []

    if siu_flag or "siu_referral" in fraud_signals:
        trace.append("siu_block")
        return PolicyEvaluationTrace(
            passed=False,
            decision="REFERRED",
            reason="siu_review_required",
            score=0.0,
            net_payable=Decimal("0"),
            rules_applied=trace,
        )

    if not policy.coverage_active:
        trace.append("coverage_inactive")
        return PolicyEvaluationTrace(False, "DECLINED", "coverage_inactive", 0.0, Decimal("0"), trace)

    if policy.regulatory_hold:
        trace.append("regulatory_hold")
        return PolicyEvaluationTrace(False, "HELD", "regulatory_hold", 0.2, Decimal("0"), trace)

    if loss_date < policy.effective_date or loss_date > policy.expiration_date:
        trace.append("loss_outside_policy_period")
        return PolicyEvaluationTrace(False, "DECLINED", "loss_outside_policy_period", 0.0, Decimal("0"), trace)

    aggregate_remaining = policy.aggregate_limit - policy.aggregate_used
    if aggregate_remaining <= 0:
        trace.append("aggregate_exhausted")
        return PolicyEvaluationTrace(False, "DECLINED", "aggregate_exhausted", 0.0, Decimal("0"), trace)

    if payout_amount > policy.per_occurrence_limit:
        trace.append("per_occurrence_limit")
        return PolicyEvaluationTrace(False, "HELD", "exceeds_per_occurrence_limit", 0.3, Decimal("0"), trace)

    net = max(Decimal("0"), payout_amount - policy.deductible)
    trace.append("deductible_applied")

    if net > aggregate_remaining:
        trace.append("aggregate_cap")
        return PolicyEvaluationTrace(False, "HELD", "exceeds_aggregate_remaining", 0.4, Decimal("0"), trace)

    if net > policy.auto_approve_limit:
        trace.append("authority_escalation")
        return PolicyEvaluationTrace(False, "HELD", "above_auto_approve_authority", 0.5, net, trace)

    if fraud_signals:
        trace.append("fraud_signals_present")
        score = max(0.3, 1.0 - 0.15 * len(fraud_signals))
        if score < 0.6:
            return PolicyEvaluationTrace(False, "REFERRED", "fraud_signals_elevated", score, Decimal("0"), trace)

    trace.append("auto_approve")
    return PolicyEvaluationTrace(True, "APPROVED", None, 1.0, net, trace)


DEFAULT_POLICIES: dict[str, PolicyContext] = {
    "POL-AUTO-001": PolicyContext(
        policy_number="POL-AUTO-001",
        coverage_line=CoverageLine.AUTO_LIABILITY,
        per_occurrence_limit=Decimal("1000000.00"),
        aggregate_limit=Decimal("2000000.00"),
        aggregate_used=Decimal("250000.00"),
        deductible=Decimal("500.00"),
        auto_approve_limit=Decimal("250000.00"),
        effective_date=date(2024, 1, 1),
        expiration_date=date(2026, 12, 31),
    ),
    "POL-PROP-001": PolicyContext(
        policy_number="POL-PROP-001",
        coverage_line=CoverageLine.PROPERTY,
        per_occurrence_limit=Decimal("5000000.00"),
        aggregate_limit=Decimal("10000000.00"),
        aggregate_used=Decimal("0"),
        deductible=Decimal("2500.00"),
        auto_approve_limit=Decimal("500000.00"),
        effective_date=date(2024, 1, 1),
        expiration_date=date(2026, 12, 31),
        jurisdiction="US-CA",
    ),
    "POL-MOTOR-UK-001": PolicyContext(
        policy_number="POL-MOTOR-UK-001",
        coverage_line=CoverageLine.AUTO_LIABILITY,
        per_occurrence_limit=Decimal("500000.00"),
        aggregate_limit=Decimal("1500000.00"),
        aggregate_used=Decimal("100000.00"),
        deductible=Decimal("250.00"),
        auto_approve_limit=Decimal("100000.00"),
        effective_date=date(2024, 1, 1),
        expiration_date=date(2026, 12, 31),
        jurisdiction="UK",
    ),
}
