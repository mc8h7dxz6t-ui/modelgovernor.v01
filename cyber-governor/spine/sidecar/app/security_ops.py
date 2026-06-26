"""Finance-adapted regulatory invariant probes."""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

from .metrics import get_counters


class RegulatoryOpsInvariantError(Exception):
    pass


def assert_security_ops_invariants(session: Session) -> dict[str, int]:
    violations: dict[str, int] = {}

    negative = session.execute(text("SELECT COUNT(*) FROM principal_budgets WHERE balance < 0")).scalar_one()
    violations["negative_balances"] = int(negative)
    if negative:
        get_counters().increment("negative_balance_detected_total", int(negative))

    cap_over = session.execute(
        text("SELECT COUNT(*) FROM action_budget_state WHERE reserved_total > cap_amount")
    ).scalar_one()
    violations["exposure_cap_overruns"] = int(cap_over)
    if cap_over:
        get_counters().increment("exposure_cap_overrun_detected_total", int(cap_over))

    if sum(violations.values()):
        raise RegulatoryOpsInvariantError(f"regulatory ops violations: {violations}")
    return violations
