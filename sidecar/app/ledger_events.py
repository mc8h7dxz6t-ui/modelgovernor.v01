"""Append-only ledger events with hash-chain sealing (K3 — reconciler + sidecar parity)."""

from __future__ import annotations

import json
import logging
from decimal import Decimal
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from .money import quantize_money as _money

logger = logging.getLogger(__name__)


def append_sealed_ledger_event(
    session: Session,
    *,
    idempotency_key: str,
    user_id: str,
    event_type: str,
    amount_delta: Decimal,
    metadata: dict[str, Any],
) -> None:
    """Insert a ledger_events row and seal it when row_hash columns exist."""
    from spine_core.chain_advisory_lock import chain_append_lock
    from spine_core.config import CHAIN_APPEND_LOCK_KEYS, GovernorDomain

    with chain_append_lock(session, lock_key=CHAIN_APPEND_LOCK_KEYS[GovernorDomain.MODEL]):
        _append_sealed_ledger_event_locked(
            session,
            idempotency_key=idempotency_key,
            user_id=user_id,
            event_type=event_type,
            amount_delta=amount_delta,
            metadata=metadata,
        )


def _append_sealed_ledger_event_locked(
    session: Session,
    *,
    idempotency_key: str,
    user_id: str,
    event_type: str,
    amount_delta: Decimal,
    metadata: dict[str, Any],
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
    _seal_last_event(
        session,
        idempotency_key=idempotency_key,
        user_id=user_id,
        event_type=event_type,
        amount_delta=_money(amount_delta),
        metadata=metadata,
    )


def _seal_last_event(
    session: Session,
    *,
    idempotency_key: str,
    user_id: str,
    event_type: str,
    amount_delta: Decimal,
    metadata: dict[str, Any],
) -> None:
    from . import ledger_seal
    from .metrics import get_counters

    if not ledger_seal.schema_supports_ledger_seal(session):
        raise RuntimeError("ledger_events seal columns unavailable — cannot append unsealed events")

    dialect = session.bind.dialect.name
    recorded_expr = "recorded_at::text" if dialect == "postgresql" else "recorded_at"

    try:
        row = session.execute(
            text(
                f"""
                SELECT event_id, amount_delta, metadata, {recorded_expr} AS recorded_at
                FROM ledger_events
                WHERE idempotency_key = :idempotency_key
                ORDER BY event_id DESC
                LIMIT 1
                """
            ),
            {"idempotency_key": idempotency_key},
        ).mappings().first()
        if not row:
            return
        metadata = metadata if isinstance(metadata, dict) else {}
        if row["metadata"]:
            try:
                parsed = json.loads(row["metadata"]) if isinstance(row["metadata"], str) else row["metadata"]
                if isinstance(parsed, dict):
                    metadata = parsed
            except json.JSONDecodeError:
                pass
        ledger_seal.seal_ledger_event(
            session,
            event_id=int(row["event_id"]),
            idempotency_key=idempotency_key,
            user_id=user_id,
            event_type=event_type,
            amount_delta=str(row["amount_delta"]),
            metadata=metadata,
            recorded_at=str(row["recorded_at"]),
        )
        get_counters().increment("ledger_event_sealed_total")
    except Exception as exc:
        get_counters().increment("ledger_event_seal_failed_total")
        logger.error("ledger event seal failed idempotency_key=%s: %s", idempotency_key, exc)
        raise
