"""Horizon sweeper — strand ambiguous crystals past Commit Horizon."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.orm import Session

_CG_ROOT = Path(__file__).resolve().parents[3]
if str(_CG_ROOT) not in sys.path:
    sys.path.insert(0, str(_CG_ROOT))
from platforms.common.crystal import should_strand_on_expiry

try:
    from app.security_events import append_security_event
    from app.metrics import get_counters
except ImportError:
    append_security_event = None  # type: ignore
    get_counters = None  # type: ignore


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def sweep_expired_horizons(session: Session, batch_size: int = 100) -> int:
    lock = "" if session.bind.dialect.name == "sqlite" else " FOR UPDATE SKIP LOCKED"
    rows = session.execute(
        text(
            f"""
            SELECT c.crystal_id, c.operation_id, c.risk_tier, c.platform,
                   e.account_id, e.reserved_budget, e.status
            FROM governance_crystals c
            JOIN security_escrow_ledger e ON e.crystal_id = c.crystal_id
            WHERE c.terminal_state IS NULL
              AND c.horizon_expires_at <= CURRENT_TIMESTAMP
              AND e.status IN ('CRYSTALLIZED', 'IN_FLIGHT', 'ACTION_TIMEOUT')
            ORDER BY c.horizon_expires_at ASC
            LIMIT :batch
            {lock}
            """
        ),
        {"batch": batch_size},
    ).mappings().all()

    swept = 0
    now = _utcnow()
    for row in rows:
        strand = should_strand_on_expiry(row["risk_tier"]) or row["status"] != "CRYSTALLIZED"
        if strand:
            session.execute(
                text("UPDATE governance_crystals SET terminal_state = 'STRANDED' WHERE crystal_id = :cid"),
                {"cid": row["crystal_id"]},
            )
            session.execute(
                text(
                    """
                    UPDATE security_escrow_ledger
                    SET status = 'STRANDED', terminal_reason = 'HORIZON_STRANDED'
                    WHERE crystal_id = :cid
                    """
                ),
                {"cid": row["crystal_id"]},
            )
            if append_security_event:
                append_security_event(
                    session,
                    operation_id=row["operation_id"],
                    crystal_id=row["crystal_id"],
                    account_id=row["account_id"],
                    event_type="STRANDED_HOLD",
                    reserve_delta=0,
                    metadata={"reason": "horizon_sweep"},
                )
            if get_counters:
                get_counters().increment("reconciler_horizon_strand_total")
        else:
            reserved = row["reserved_budget"]
            session.execute(
                text(
                    """
                    UPDATE security_budget_ledgers SET balance = balance + :amt, updated_at = :now
                    WHERE account_id = :a AND ledger_type = 'case' AND currency = 'USD'
                    """
                ),
                {"amt": reserved, "now": now.isoformat() if session.bind.dialect.name == "sqlite" else now, "a": row["account_id"]},
            )
            session.execute(
                text("UPDATE governance_crystals SET terminal_state = 'EXPIRED' WHERE crystal_id = :cid"),
                {"cid": row["crystal_id"]},
            )
            session.execute(
                text(
                    """
                    UPDATE security_escrow_ledger
                    SET status = 'EXPIRED', terminal_reason = 'HORIZON_EXPIRED'
                    WHERE crystal_id = :cid
                    """
                ),
                {"cid": row["crystal_id"]},
            )
            if append_security_event:
                append_security_event(
                    session,
                    operation_id=row["operation_id"],
                    crystal_id=row["crystal_id"],
                    account_id=row["account_id"],
                    event_type="HORIZON_EXPIRED",
                    reserve_delta=reserved,
                    metadata={"reason": "horizon_sweep"},
                )
            if get_counters:
                get_counters().increment("reconciler_expired_total")
        swept += 1
    session.commit()
    return swept
