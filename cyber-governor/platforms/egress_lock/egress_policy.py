"""Egress policy evaluation — blocks ungoverned data movement."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class EgressPolicy:
    max_bytes_without_review: int
    blocked_destinations: frozenset[str]


@dataclass(frozen=True)
class EgressEvaluation:
    approved: bool
    reason: str | None
    risk_score: float


def evaluate_egress(
    *,
    destination: str,
    byte_count: int,
    principal_id: str,
    policy: EgressPolicy,
) -> EgressEvaluation:
    dest = destination.lower().strip()
    if dest in policy.blocked_destinations:
        return EgressEvaluation(False, f"destination blocked: {destination}", 1.0)
    if byte_count > policy.max_bytes_without_review:
        return EgressEvaluation(
            False,
            f"byte_count {byte_count} exceeds threshold {policy.max_bytes_without_review}",
            0.9,
        )
    if not principal_id or principal_id == "unknown":
        return EgressEvaluation(False, "unknown principal", 0.8)
    return EgressEvaluation(True, None, 0.1)
