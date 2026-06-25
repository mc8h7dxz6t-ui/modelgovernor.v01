"""Reserve reconciliation — claim reserve vs reinsurance / IC ledger (D&O operational risk)."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class ReconcileEvaluation:
    matched: bool
    decision: str
    match_state: str
    drift_amount: Decimal
    reason: str | None


def evaluate_reserve_match(
    *,
    claim_id: str,
    case_reserve: Decimal,
    reinsurance_reserve: Decimal,
    ic_ledger_reserve: Decimal | None = None,
    tolerance_pct: Decimal = Decimal("0.02"),
    jurisdiction: str = "US",
) -> ReconcileEvaluation:
    reference = ic_ledger_reserve if ic_ledger_reserve is not None else reinsurance_reserve
    if reference <= 0:
        return ReconcileEvaluation(False, "REFERRED", "PENDING", Decimal("0"), "missing_reinsurance_data")

    drift = abs(case_reserve - reference)
    threshold = max(Decimal("100"), reference * tolerance_pct)

    if drift > threshold:
        return ReconcileEvaluation(
            False,
            "DRIFT",
            "DRIFT",
            drift,
            f"reserve_drift_exceeds_{tolerance_pct:.0%}",
        )

    if drift > threshold * Decimal("0.5"):
        return ReconcileEvaluation(True, "WARN", "WARN", drift, "immaterial_drift")

    return ReconcileEvaluation(True, "MATCHED", "MATCHED", drift, None)
