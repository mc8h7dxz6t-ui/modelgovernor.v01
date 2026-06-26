"""Security-plane invariant probes — zero error budget."""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

from .metrics import get_counters


class SecurityOpsInvariantError(Exception):
    pass


def assert_security_ops_invariants(session: Session) -> dict[str, int]:
    violations: dict[str, int] = {}

    negative = session.execute(text("SELECT COUNT(*) FROM security_budget_ledgers WHERE balance < 0")).scalar_one()
    violations["negative_balances"] = int(negative)
    if negative:
        get_counters().increment("negative_balance_detected_total", int(negative))

    cap_over = session.execute(
        text("SELECT COUNT(*) FROM aggregate_limit_state WHERE reserved_total > cap_amount")
    ).scalar_one()
    violations["aggregate_cap_overruns"] = int(cap_over)
    if cap_over:
        get_counters().increment("aggregate_cap_overrun_detected_total", int(cap_over))

    committed_without_crystal = session.execute(
        text(
            """
            SELECT COUNT(*) FROM security_escrow_ledger e
            WHERE e.status = 'COMMITTED'
              AND NOT EXISTS (
                SELECT 1 FROM governance_crystals c
                WHERE c.crystal_id = e.crystal_id AND c.terminal_state = 'COMMITTED'
              )
            """
        )
    ).scalar_one()
    violations["committed_without_crystal"] = int(committed_without_crystal)
    if committed_without_crystal:
        get_counters().increment("surprise_commit_blocked_total", int(committed_without_crystal))

    high_risk_auto_expired = session.execute(
        text(
            """
            SELECT COUNT(*) FROM governance_crystals c
            JOIN security_policy_registry p ON c.policy_id = p.policy_id
            WHERE c.terminal_state = 'EXPIRED'
              AND p.risk_classification IN ('critical', 'high')
              AND p.allow_auto_expire = FALSE
            """
        )
    ).scalar_one()
    violations["high_risk_auto_expired"] = int(high_risk_auto_expired)
    if high_risk_auto_expired:
        get_counters().increment("high_risk_auto_expired_total", int(high_risk_auto_expired))

    duplicate_commits = session.execute(
        text(
            """
            SELECT COUNT(*) FROM (
                SELECT operation_id FROM security_events
                WHERE event_type = 'COMMITTED_FINAL'
                GROUP BY operation_id HAVING COUNT(*) > 1
            ) d
            """
        )
    ).scalar_one()
    violations["duplicate_commits"] = int(duplicate_commits)
    if duplicate_commits:
        get_counters().increment("duplicate_commit_anomaly_total", int(duplicate_commits))

    duplicate_refunds = session.execute(
        text(
            """
            SELECT COUNT(*) FROM (
                SELECT operation_id FROM security_events
                WHERE event_type IN ('HORIZON_EXPIRED', 'EXPIRED_SWEEP')
                GROUP BY operation_id HAVING COUNT(*) > 1
            ) d
            """
        )
    ).scalar_one()
    violations["duplicate_refunds"] = int(duplicate_refunds)
    if duplicate_refunds:
        get_counters().increment("duplicate_refund_anomaly_total", int(duplicate_refunds))

    stranded_without_hold = session.execute(
        text(
            """
            SELECT COUNT(*) FROM security_escrow_ledger e
            WHERE e.status = 'STRANDED'
              AND NOT EXISTS (
                SELECT 1 FROM security_events ev
                WHERE ev.operation_id = e.operation_id AND ev.event_type = 'STRANDED_HOLD'
              )
            """
        )
    ).scalar_one()
    violations["stranded_without_hold"] = int(stranded_without_hold)
    if stranded_without_hold:
        get_counters().increment("stranded_without_hold_total", int(stranded_without_hold))

    if sum(violations.values()):
        raise SecurityOpsInvariantError(f"security ops violations: {violations}")
    return violations
