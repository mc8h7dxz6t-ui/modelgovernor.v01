"""AI Finance Ops Finals — settlement and reconciliation invariant probes."""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.orm import Session

from .metrics import get_counters

MONEY_QUANTUM = Decimal("0.000001")


class FinanceOpsInvariantError(Exception):
    pass


def assert_finance_ops_invariants(session: Session) -> dict[str, int]:
    """Session-wide finance-plane invariant audit for institutional++ proof runs."""
    violations: dict[str, int] = {}

    negative_wallets = session.execute(
        text("SELECT COUNT(*) FROM user_wallets WHERE balance < 0")
    ).scalar_one()
    violations["negative_wallets"] = int(negative_wallets)
    if negative_wallets:
        get_counters().increment("negative_wallet_detected_total", int(negative_wallets))

    cap_overruns = session.execute(
        text(
            """
            SELECT COUNT(*) FROM trace_budget_state
            WHERE reserved_total > cap_amount
            """
        )
    ).scalar_one()
    violations["trace_cap_overruns"] = int(cap_overruns)
    if cap_overruns:
        get_counters().increment("trace_cap_overrun_detected_total", int(cap_overruns))

    duplicate_refunds = session.execute(
        text(
            """
            SELECT COUNT(*) FROM (
                SELECT idempotency_key
                FROM ledger_events
                WHERE event_type = 'EXPIRED_SWEEP'
                GROUP BY idempotency_key
                HAVING COUNT(*) > 1
            ) dup
            """
        )
    ).scalar_one()
    violations["duplicate_refunds"] = int(duplicate_refunds)
    if duplicate_refunds:
        get_counters().increment("duplicate_refund_anomaly_total", int(duplicate_refunds))

    duplicate_settlements = session.execute(
        text(
            """
            SELECT COUNT(*) FROM (
                SELECT idempotency_key
                FROM ledger_events
                WHERE event_type IN ('SETTLED_FINAL', 'RECONCILED_LATE_SETTLE')
                GROUP BY idempotency_key
                HAVING COUNT(*) > 1
            ) dup
            """
        )
    ).scalar_one()
    violations["duplicate_settlements"] = int(duplicate_settlements)
    if duplicate_settlements:
        get_counters().increment("duplicate_settlement_anomaly_total", int(duplicate_settlements))

    stranded_without_hold = session.execute(
        text(
            """
            SELECT COUNT(*) FROM escrow_ledger e
            WHERE e.status = 'STRANDED'
              AND NOT EXISTS (
                SELECT 1 FROM ledger_events le
                WHERE le.idempotency_key = e.idempotency_key
                  AND le.event_type = 'STRANDED_HOLD'
              )
            """
        )
    ).scalar_one()
    violations["stranded_without_hold_event"] = int(stranded_without_hold)

    total = sum(violations.values())
    if total:
        raise FinanceOpsInvariantError(f"finance ops invariant violations: {violations}")
    return violations
