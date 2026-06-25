"""Mock credit inference rail."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class RailOutcome:
    decision: str
    score: float
    explanation_id: str
    latency_ms: int


def score_application(*, exposure: Decimal, model_version_id: str) -> RailOutcome:
    if model_version_id.startswith("unapproved"):
        return RailOutcome(decision="BLOCKED", score=0.0, explanation_id="exp-model-block", latency_ms=12)
    if exposure > Decimal("250000"):
        return RailOutcome(decision="REFER", score=0.55, explanation_id="exp-high-exposure", latency_ms=18)
    return RailOutcome(decision="APPROVE", score=0.82, explanation_id="exp-auto-approve", latency_ms=15)
