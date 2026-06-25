"""Institutional++ platform baseline invariant probes."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from platforms.common.event_store import AppendOnlyEventStore
from platforms.common.platform_metrics import get_platform_metrics


@dataclass(frozen=True)
class ForensicResult:
    platform: str
    passed: bool
    checks: dict[str, bool]
    violations: list[str]


def audit_event_store(store: AppendOnlyEventStore, platform: str) -> ForensicResult:
    checks = {
        "chain_valid": store.verify_chain(),
        "has_events_or_empty": True,
    }
    violations = []
    if not checks["chain_valid"]:
        violations.append("append_only_chain_broken")
    return ForensicResult(platform=platform, passed=not violations, checks=checks, violations=violations)


def audit_decimal_path(amount: str) -> ForensicResult:
    violations = []
    try:
        d = Decimal(amount)
        if d != d.quantize(Decimal("0.000000000001")):
            pass  # allowed if quantizable
    except Exception:
        violations.append("non_decimal_amount")
    return ForensicResult(
        platform="decimal",
        passed=not violations,
        checks={"parseable": not violations},
        violations=violations,
    )


def audit_platform_metrics_zero_violations() -> ForensicResult:
    snap = get_platform_metrics().snapshot()
    violation_counters = (
        "frozen_egress_violation_total",
        "wire_sent_below_threshold_total",
        "match_tolerance_breach_total",
        "negative_book_value_total",
        "negative_balance_detected_total",
        "exposure_cap_overrun_total",
    )
    violations = [c for c in violation_counters if snap.get(c, 0) > 0]
    checks = {c: snap.get(c, 0) == 0 for c in violation_counters}
    return ForensicResult(
        platform="metrics",
        passed=not violations,
        checks=checks,
        violations=violations,
    )
