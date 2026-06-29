"""Append-only sealed claim events — shared by sidecar and reconciler."""
from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from .claim_seal import GENESIS_HASH, compute_row_hash, head_hash, schema_supports_claim_seal
from .currency import quantize_money

_append_lock = threading.Lock()


def _money_param(value: Decimal) -> str | Decimal:
    return str(quantize_money(value))


def append_claim_event(
    session: Session,
    *,
    operation_id: str,
    crystal_id: str | None,
    account_id: str,
    event_type: str,
    reserve_delta: Decimal,
    metadata: dict[str, Any],
) -> int:
    if not schema_supports_claim_seal(session):
        raise RuntimeError("claim_events seal columns unavailable")

    with _append_lock:
        prev = head_hash(session) or GENESIS_HASH
        now = datetime.now(timezone.utc)
        meta_sql = ":meta" if session.bind.dialect.name == "sqlite" else "CAST(:meta AS jsonb)"
        event_id = session.execute(
            text(
                f"""
                INSERT INTO claim_events (
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
                "reserve_delta": _money_param(reserve_delta),
                "meta": json.dumps(metadata),
                "prev_hash": prev,
                "placeholder": prev,
                "recorded_at": now.isoformat() if session.bind.dialect.name == "sqlite" else now,
            },
        ).scalar_one()
        rh = compute_row_hash(
            event_id=event_id,
            operation_id=operation_id,
            crystal_id=crystal_id,
            account_id=account_id,
            event_type=event_type,
            reserve_delta=str(quantize_money(reserve_delta)),
            metadata=metadata,
            prev_hash=prev,
            recorded_at=now.isoformat(),
        )
        session.execute(
            text("UPDATE claim_events SET row_hash = :rh WHERE event_id = :eid"),
            {"rh": rh, "eid": event_id},
        )
        return event_id
