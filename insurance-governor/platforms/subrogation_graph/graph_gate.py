"""Subrogation recovery gate — governed desk evidence envelope (live desk API = SOW)."""
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


def _normalize_defendants(defendants: dict[str, float]) -> dict[str, float]:
    total = sum(defendants.values())
    if total <= 1.0 or total == 0:
        return defendants
    return {name: score / total for name, score in defendants.items()}


def evaluate_subrogation_graph(
    *,
    claim_id: str,
    total_loss: Decimal,
    defendants: dict[str, float],
    min_liability_pct: float = 0.25,
    salvage_offset: Decimal = Decimal("0"),
    statute_expired: bool = False,
) -> SubrogationEvaluation:
    del claim_id
    if statute_expired:
        return SubrogationEvaluation(False, "REFERRED", Decimal("0"), "", 0.0, "statute_expired")
    if not defendants:
        return SubrogationEvaluation(False, "NO_RECOVERY", Decimal("0"), "", 0.0, "no_defendants")

    normalized = _normalize_defendants(defendants)
    primary = max(normalized, key=normalized.get)  # type: ignore[arg-type]
    score = normalized[primary]
    if score < min_liability_pct:
        return SubrogationEvaluation(False, "REFERRED", Decimal("0"), primary, score, "liability_below_threshold")

    gross = total_loss * Decimal(str(score))
    recovery = max(Decimal("0"), gross - salvage_offset)
    if recovery <= Decimal("0"):
        return SubrogationEvaluation(False, "NO_RECOVERY", Decimal("0"), primary, score, "salvage_offsets_recovery")

    return SubrogationEvaluation(True, "RECOVERY_APPROVED", recovery, primary, score, None)
