"""Hash chaining for decision_events."""
from __future__ import annotations

import hashlib
import json
from typing import Any

GENESIS_HASH = "0" * 64


def compute_row_hash(
    *,
    event_id: int,
    operation_id: str,
    crystal_id: str | None,
    account_id: str,
    event_type: str,
    exposure_delta: str,
    metadata: dict[str, Any],
    prev_hash: str,
    recorded_at: str,
) -> str:
    body = json.dumps(
        {
            "event_id": event_id,
            "operation_id": operation_id,
            "crystal_id": crystal_id,
            "account_id": account_id,
            "event_type": event_type,
            "exposure_delta": exposure_delta,
            "metadata": metadata,
            "prev_hash": prev_hash,
            "recorded_at": recorded_at,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(body.encode()).hexdigest()


def head_hash(session) -> str | None:
    from sqlalchemy import text

    row = session.execute(
        text("SELECT row_hash FROM decision_events ORDER BY event_id DESC LIMIT 1")
    ).first()
    return row[0] if row else None
