"""Subrogation graph scoring — multi-defendant liability routing."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class SubrogationEvaluation:
    recoverable: bool
    decision: str
    recovery_amount: Decimal
    primary_defendant: str
    graph_score: float
    reason: str | None


def evaluate_subrogation_graph(
    *,
    claim_id: str,
    total_loss: Decimal,
    defendants: dict[str, float],
    min_liability_pct: float = 0.25,
) -> SubrogationEvaluation:
    if not defendants:
        return SubrogationEvaluation(False, "NO_RECOVERY", Decimal("0"), "", 0.0, "no_defendants")
    primary = max(defendants, key=defendants.get)  # type: ignore[arg-type]
    score = defendants[primary]
    if score < min_liability_pct:
        return SubrogationEvaluation(False, "REFERRED", Decimal("0"), primary, score, "liability_below_threshold")
    recovery = total_loss * Decimal(str(score))
    return SubrogationEvaluation(True, "RECOVERY_APPROVED", recovery, primary, score, None)
