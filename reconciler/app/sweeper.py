from __future__ import annotations

import json
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.orm import Session

try:
    from sidecar.app.metrics import get_counters as _get_counters
except ImportError:
    _get_counters = None  # type: ignore[assignment]

MONEY_QUANTUM = Decimal("0.000001")


def sweep_expired_reservations(session: Session, batch_size: int = 100) -> int:
    lock_clause = "" if session.bind.dialect.name == "sqlite" else " FOR UPDATE SKIP LOCKED"
    rows = session.execute(
        text(
            f"""
            SELECT idempotency_key, user_id, trace_id, reserved_amount, status
            FROM escrow_ledger
            WHERE status IN ('RESERVED', 'IN_FLIGHT', 'PROVIDER_TIMEOUT')
              AND expires_at <= CURRENT_TIMESTAMP
            ORDER BY expires_at ASC
            LIMIT :batch_size
            {lock_clause}
            """
        ),
        {"batch_size": batch_size},
    ).mappings().all()

    swept = 0
    for row in rows:
        now = _utcnow()
        if row["status"] in {"IN_FLIGHT", "PROVIDER_TIMEOUT"} or _has_open_attempts(
            session, row["idempotency_key"]
        ):
            session.execute(
                text(
                    """
                    UPDATE escrow_ledger
                    SET status = 'STRANDED',
                        expired_at = :expired_at,
                        terminal_reason = :terminal_reason
                    WHERE idempotency_key = :idempotency_key
                    """
                ),
                {
                    "expired_at": now,
                    "terminal_reason": "STRANDED_HOLD_PENDING_RECONCILIATION",
                    "idempotency_key": row["idempotency_key"],
                },
            )
            _append_event(
                session,
                idempotency_key=row["idempotency_key"],
                user_id=row["user_id"],
                event_type="STRANDED_HOLD",
                amount_delta=Decimal("0"),
                metadata={"reason": "reconciler_expiry_claim"},
            )
            if _get_counters is not None:
                _get_counters().increment("reconciler_stranded_total")
        else:
            reserved_amount = _money(row["reserved_amount"])
            session.execute(
                text(
                    """
                    UPDATE user_wallets
                    SET balance = balance + :reserved_amount,
                        updated_at = :updated_at
                    WHERE user_id = :user_id
                    """
                ),
                {
                    "reserved_amount": reserved_amount,
                    "updated_at": now,
                    "user_id": row["user_id"],
                },
            )
            session.execute(
                text(
                    """
                    UPDATE trace_budget_state
                    SET reserved_total = reserved_total - :reserved_amount,
                        updated_at = :updated_at
                    WHERE trace_id = :trace_id
                    """
                ),
                {
                    "reserved_amount": reserved_amount,
                    "updated_at": now,
                    "trace_id": row["trace_id"],
                },
            )
            session.execute(
                text(
                    """
                    UPDATE escrow_ledger
                    SET status = 'EXPIRED',
                        expired_at = :expired_at,
                        terminal_reason = :terminal_reason
                    WHERE idempotency_key = :idempotency_key
                    """
                ),
                {
                    "expired_at": now,
                    "terminal_reason": "TTL_EXPIRED",
                    "idempotency_key": row["idempotency_key"],
                },
            )
            _append_event(
                session,
                idempotency_key=row["idempotency_key"],
                user_id=row["user_id"],
                event_type="EXPIRED_SWEEP",
                amount_delta=reserved_amount,
                metadata={"reason": "reconciler_expiry_claim"},
            )
            _detect_duplicate_refund_events(session, row["idempotency_key"])
            if _get_counters is not None:
                _get_counters().increment("reconciler_expired_total")
        swept += 1

    session.commit()
    if _get_counters is not None:
        _get_counters().increment("reconciler_claimed_total", swept)
    return swept


def _has_open_attempts(session: Session, idempotency_key: str) -> bool:
    row = session.execute(
        text(
            """
            SELECT 1
            FROM provider_dispatch_attempts
            WHERE idempotency_key = :idempotency_key
              AND status IN ('IN_FLIGHT', 'PROVIDER_TIMEOUT')
            LIMIT 1
            """
        ),
        {"idempotency_key": idempotency_key},
    ).first()
    return row is not None


def _append_event(
    session: Session,
    *,
    idempotency_key: str,
    user_id: str,
    event_type: str,
    amount_delta: Decimal,
    metadata: dict,
) -> None:
    metadata_json = json.dumps(metadata, sort_keys=True)
    metadata_value = ":metadata"
    if session.bind.dialect.name == "postgresql":
        metadata_value = "CAST(:metadata AS JSONB)"

    session.execute(
        text(
            f"""
            INSERT INTO ledger_events (idempotency_key, user_id, event_type, amount_delta, metadata)
            VALUES (:idempotency_key, :user_id, :event_type, :amount_delta, {metadata_value})
            """
        ),
        {
            "idempotency_key": idempotency_key,
            "user_id": user_id,
            "event_type": event_type,
            "amount_delta": _money(amount_delta),
            "metadata": metadata_json,
        },
    )


def _detect_duplicate_refund_events(session: Session, idempotency_key: str) -> None:
    row = session.execute(
        text(
            """
            SELECT COUNT(*) AS cnt
            FROM ledger_events
            WHERE idempotency_key = :idempotency_key
              AND event_type = 'EXPIRED_SWEEP'
            """
        ),
        {"idempotency_key": idempotency_key},
    ).mappings().first()
    if row and int(row["cnt"]) > 1 and _get_counters is not None:
        _get_counters().increment("duplicate_refund_anomaly_total")


def _money(value: Decimal | str | int | float | None) -> Decimal:
    return Decimal(value or 0).quantize(MONEY_QUANTUM)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)
