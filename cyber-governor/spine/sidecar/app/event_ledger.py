"""Append-only security_events with hash chain sealing."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from .currency import quantize_money
from .security_seal import GENESIS_HASH, compute_row_hash, head_hash


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _money_param(value: Decimal) -> str | Decimal:
    return str(quantize_money(value))


def append_security_event(
    session: Session,
    *,
    operation_id: str,
    crystal_id: str | None,
    account_id: str,
    event_type: str,
    exposure_delta: Decimal = Decimal("0"),
    metadata: dict[str, Any] | None = None,
) -> int:
    meta = metadata or {}
    prev = head_hash(session) or GENESIS_HASH
    now = _utcnow()
    meta_sql = ":meta" if session.bind.dialect.name == "sqlite" else ":meta::jsonb"
    recorded_at_value = now.isoformat() if session.bind.dialect.name == "sqlite" else now
    row = session.execute(
        text(
            f"""
            INSERT INTO security_events (
                operation_id, crystal_id, account_id, event_type,
                exposure_delta, metadata, prev_hash, row_hash, recorded_at
            ) VALUES (
                :operation_id, :crystal_id, :account_id, :event_type,
                :exposure_delta, {meta_sql}, :prev_hash, :placeholder, :recorded_at
            )
            RETURNING event_id
            """
        ),
        {
            "operation_id": operation_id,
            "crystal_id": crystal_id,
            "account_id": account_id,
            "event_type": event_type,
            "exposure_delta": _money_param(exposure_delta),
            "meta": json.dumps(meta),
            "prev_hash": prev,
            "placeholder": prev,
            "recorded_at": recorded_at_value,
        },
    ).scalar_one()
    recorded_at_for_hash = recorded_at_value if isinstance(recorded_at_value, str) else now.isoformat()
    rh = compute_row_hash(
        event_id=row,
        operation_id=operation_id,
        crystal_id=crystal_id,
        account_id=account_id,
        event_type=event_type,
        exposure_delta=str(quantize_money(exposure_delta)),
        metadata=meta,
        prev_hash=prev,
        recorded_at=recorded_at_for_hash,
    )
    session.execute(
        text("UPDATE security_events SET row_hash = :rh, prev_hash = :prev WHERE event_id = :eid"),
        {"rh": rh, "prev": prev, "eid": row},
    )
    return int(row)
