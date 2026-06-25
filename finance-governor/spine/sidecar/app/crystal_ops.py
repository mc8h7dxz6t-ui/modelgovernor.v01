"""CCP invariant probes — Surprise Budget = 0."""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

from .metrics import get_counters


class CrystalOpsInvariantError(Exception):
    pass


def assert_crystal_ops_invariants(session: Session) -> dict[str, int]:
    violations: dict[str, int] = {}

    committed_without_crystal = session.execute(
        text(
            """
            SELECT COUNT(*) FROM commit_escrow_ledger e
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
            JOIN instrument_policy_registry p ON c.policy_id = p.policy_id
            WHERE c.terminal_state = 'EXPIRED'
              AND p.risk_classification IN ('critical', 'high')
              AND p.allow_auto_expire = FALSE
            """
        )
    ).scalar_one()
    violations["high_risk_auto_expired"] = int(high_risk_auto_expired)

    duplicate_commits = session.execute(
        text(
            """
            SELECT COUNT(*) FROM (
                SELECT operation_id FROM decision_events
                WHERE event_type = 'COMMITTED_FINAL'
                GROUP BY operation_id HAVING COUNT(*) > 1
            ) d
            """
        )
    ).scalar_one()
    violations["duplicate_commits"] = int(duplicate_commits)
    if duplicate_commits:
        get_counters().increment("duplicate_commit_anomaly_total", int(duplicate_commits))

    if sum(violations.values()):
        raise CrystalOpsInvariantError(f"crystal ops violations: {violations}")
    return violations
