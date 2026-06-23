"""Tamper-evident hash chaining for ledger_events (enterprise audit trail)."""
from __future__ import annotations

import hashlib
import json
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

GENESIS_HASH = "0" * 64


def schema_supports_ledger_seal(session: Session) -> bool:
    if session.bind.dialect.name != "postgresql":
        return False
    row = session.execute(
        text(
            """
            SELECT 1
            FROM information_schema.columns
            WHERE table_name = 'ledger_events' AND column_name = 'row_hash'
            """
        )
    ).first()
    return row is not None


def seal_ledger_event(
    session: Session,
    *,
    event_id: int,
    idempotency_key: str,
    user_id: str,
    event_type: str,
    amount_delta: str,
    metadata: dict[str, Any],
    recorded_at: str,
) -> tuple[str, str]:
    prev_hash = session.execute(
        text(
            """
            SELECT row_hash FROM ledger_events
            WHERE row_hash IS NOT NULL
            ORDER BY event_id DESC
            LIMIT 1
            """
        )
    ).scalar_one_or_none() or GENESIS_HASH

    payload = json.dumps(
        {
            "event_id": event_id,
            "idempotency_key": idempotency_key,
            "user_id": user_id,
            "event_type": event_type,
            "amount_delta": amount_delta,
            "metadata": metadata,
            "recorded_at": recorded_at,
            "prev_hash": prev_hash,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    row_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    session.execute(
        text(
            """
            UPDATE ledger_events
            SET prev_hash = :prev_hash, row_hash = :row_hash
            WHERE event_id = :event_id
            """
        ),
        {"prev_hash": prev_hash, "row_hash": row_hash, "event_id": event_id},
    )
    return prev_hash, row_hash
