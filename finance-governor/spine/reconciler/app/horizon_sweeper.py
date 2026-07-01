"""Horizon sweeper — strand ambiguous crystals past Commit Horizon."""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.orm import Session

_FG_ROOT = Path(__file__).resolve().parents[3]
if str(_FG_ROOT) not in sys.path:
    sys.path.insert(0, str(_FG_ROOT))
from platforms.common.crystal import should_strand_on_expiry

_SIDECAR = Path(__file__).resolve().parents[2] / "sidecar"
if str(_SIDECAR) not in sys.path:
    sys.path.insert(0, str(_SIDECAR))
from app.decision_seal import append_decision_event

try:
    from app.metrics import get_counters
except ImportError:
    get_counters = None  # type: ignore


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def sweep_expired_horizons(session: Session, batch_size: int = 100) -> int:
    lock = "" if session.bind.dialect.name == "sqlite" else " FOR UPDATE SKIP LOCKED"
    rows = session.execute(
        text(
            f"""
            SELECT c.crystal_id, c.operation_id, c.risk_tier, c.platform,
                   e.account_id, e.reserved_exposure, e.status
            FROM governance_crystals c
            JOIN commit_escrow_ledger e ON e.crystal_id = c.crystal_id
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
                text(
                    """
                    UPDATE governance_crystals SET terminal_state = 'STRANDED' WHERE crystal_id = :cid
                    """
                ),
                {"cid": row["crystal_id"]},
            )
            session.execute(
                text(
                    """
                    UPDATE commit_escrow_ledger
                    SET status = 'STRANDED', terminal_reason = 'HORIZON_STRANDED'
                    WHERE crystal_id = :cid
                    """
                ),
                {"cid": row["crystal_id"]},
            )
            append_decision_event(
                session,
                operation_id=row["operation_id"],
                crystal_id=row["crystal_id"],
                account_id=row["account_id"],
                event_type="STRANDED_HOLD",
                exposure_delta=Decimal("0"),
                metadata={"reason": "horizon_sweep"},
            )
            if get_counters:
                get_counters().increment("reconciler_horizon_strand_total")
        else:
            reserved = row["reserved_exposure"]
            session.execute(
                text(
                    """
                    UPDATE account_ledgers SET balance = balance + :amt, updated_at = :now
                    WHERE account_id = :a AND ledger_type = 'exposure' AND currency = 'USD'
                    """
                ),
                {"amt": reserved, "now": now, "a": row["account_id"]},
            )
            session.execute(
                text("UPDATE governance_crystals SET terminal_state = 'EXPIRED' WHERE crystal_id = :cid"),
                {"cid": row["crystal_id"]},
            )
            session.execute(
                text(
                    """
                    UPDATE commit_escrow_ledger
                    SET status = 'EXPIRED', terminal_reason = 'HORIZON_EXPIRED'
                    WHERE crystal_id = :cid
                    """
                ),
                {"cid": row["crystal_id"]},
            )
            append_decision_event(
                session,
                operation_id=row["operation_id"],
                crystal_id=row["crystal_id"],
                account_id=row["account_id"],
                event_type="HORIZON_EXPIRED",
                exposure_delta=Decimal(str(reserved)),
                metadata={"reason": "horizon_sweep"},
            )
            if get_counters:
                get_counters().increment("reconciler_expired_total")
        swept += 1
    session.commit()
    return swept
