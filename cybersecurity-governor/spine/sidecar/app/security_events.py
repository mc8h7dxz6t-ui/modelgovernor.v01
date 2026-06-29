"""Append-only sealed security events — shared by sidecar and reconciler."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from .security_seal import (
    GENESIS_HASH,
    head_hash,
    schema_supports_security_seal,
    seal_security_event,
)
from .currency import quantize_money


def append_security_event(
    session: Session,
    *,
    operation_id: str,
    crystal_id: str | None,
    account_id: str,
    event_type: str,
    reserve_delta: Decimal,
    metadata: dict[str, Any],
) -> int:
    if not schema_supports_security_seal(session):
        raise RuntimeError("security_events seal columns unavailable")

    prev = head_hash(session) or GENESIS_HASH
    now = datetime.now(timezone.utc)
    meta_sql = ":meta" if session.bind.dialect.name == "sqlite" else "CAST(:meta AS jsonb)"
    recorded_at_param = now.isoformat() if session.bind.dialect.name == "sqlite" else now
    amount = str(quantize_money(reserve_delta))

    event_id = session.execute(
        text(
            f"""
            INSERT INTO security_events (
                operation_id, crystal_id, account_id, event_type,
                reserve_delta, metadata, prev_hash, row_hash, recorded_at
            ) VALUES (
                :operation_id, :crystal_id, :account_id, :event_type,
                :reserve_delta, {meta_sql}, :prev_hash, :placeholder, :recorded_at
            )
            RETURNING event_id
            """
        ),
        {
            "operation_id": operation_id,
            "crystal_id": crystal_id,
            "account_id": account_id,
            "event_type": event_type,
            "reserve_delta": amount,
            "meta": json.dumps(metadata, sort_keys=True),
            "prev_hash": prev,
            "placeholder": prev,
            "recorded_at": recorded_at_param,
        },
    ).scalar_one()

    dialect = session.bind.dialect.name
    recorded_expr = "recorded_at::text" if dialect == "postgresql" else "recorded_at"
    row = session.execute(
        text(f"SELECT {recorded_expr} AS recorded_at FROM security_events WHERE event_id = :eid"),
        {"eid": event_id},
    ).mappings().first()
    recorded_at = str(row["recorded_at"]) if row else now.isoformat()

    seal_security_event(
        session,
        event_id=int(event_id),
        operation_id=operation_id,
        crystal_id=crystal_id,
        account_id=account_id,
        event_type=event_type,
        reserve_delta=amount,
        metadata=metadata,
        recorded_at=recorded_at,
    )
    return int(event_id)
