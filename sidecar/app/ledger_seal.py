"""Tamper-evident hash chaining for ledger_events (enterprise audit trail)."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

GENESIS_HASH = "0" * 64


@dataclass(frozen=True)
class LedgerChainBreak:
    event_id: int
    reason: str


@dataclass
class LedgerChainVerificationResult:
    valid: bool
    sealed_count: int
    unsealed_count: int
    total_events: int
    head_hash: str | None
    first_break: LedgerChainBreak | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "valid": self.valid,
            "sealed_count": self.sealed_count,
            "unsealed_count": self.unsealed_count,
            "total_events": self.total_events,
            "head_hash": self.head_hash,
        }
        if self.first_break is not None:
            payload["first_break"] = {
                "event_id": self.first_break.event_id,
                "reason": self.first_break.reason,
            }
        return payload


def schema_supports_ledger_seal(session: Session) -> bool:
    dialect = session.bind.dialect.name
    if dialect == "postgresql":
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
    if dialect == "sqlite":
        rows = session.execute(text("PRAGMA table_info(ledger_events)")).fetchall()
        return any(str(column[1]) == "row_hash" for column in rows)
    return False


def _normalize_metadata(metadata: Any) -> dict[str, Any]:
    if metadata is None:
        return {}
    if isinstance(metadata, dict):
        return metadata
    if isinstance(metadata, str):
        try:
            parsed = json.loads(metadata)
        except json.JSONDecodeError:
            return {}
        if isinstance(parsed, dict):
            return parsed
    return {}


def compute_row_hash(
    *,
    event_id: int,
    idempotency_key: str,
    user_id: str,
    event_type: str,
    amount_delta: str,
    metadata: dict[str, Any],
    recorded_at: str,
    prev_hash: str,
) -> str:
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
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


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

    row_hash = compute_row_hash(
        event_id=event_id,
        idempotency_key=idempotency_key,
        user_id=user_id,
        event_type=event_type,
        amount_delta=amount_delta,
        metadata=metadata,
        recorded_at=recorded_at,
        prev_hash=prev_hash,
    )
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


def verify_ledger_chain(session: Session) -> LedgerChainVerificationResult:
    if not schema_supports_ledger_seal(session):
        return LedgerChainVerificationResult(
            valid=True,
            sealed_count=0,
            unsealed_count=0,
            total_events=0,
            head_hash=None,
        )

    rows = session.execute(
        text(
            """
            SELECT
                event_id,
                idempotency_key,
                user_id,
                event_type,
                amount_delta,
                metadata,
                recorded_at,
                prev_hash,
                row_hash
            FROM ledger_events
            ORDER BY event_id ASC
            """
        )
    ).mappings().all()

    last_sealed_hash = GENESIS_HASH
    sealed_count = 0
    unsealed_count = 0
    head_hash: str | None = None
    first_break: LedgerChainBreak | None = None

    for row in rows:
        row_hash = row["row_hash"]
        if row_hash is None:
            unsealed_count += 1
            continue

        metadata = _normalize_metadata(row["metadata"])
        amount_delta = str(row["amount_delta"])
        recorded_at = str(row["recorded_at"])
        prev_hash = row["prev_hash"] or GENESIS_HASH

        if prev_hash != last_sealed_hash:
            first_break = LedgerChainBreak(
                event_id=int(row["event_id"]),
                reason=f"prev_hash mismatch at event_id={row['event_id']}",
            )
            break

        expected_hash = compute_row_hash(
            event_id=int(row["event_id"]),
            idempotency_key=row["idempotency_key"],
            user_id=row["user_id"],
            event_type=row["event_type"],
            amount_delta=amount_delta,
            metadata=metadata,
            recorded_at=recorded_at,
            prev_hash=prev_hash,
        )
        if row_hash != expected_hash:
            first_break = LedgerChainBreak(
                event_id=int(row["event_id"]),
                reason=f"row_hash mismatch at event_id={row['event_id']}",
            )
            break

        sealed_count += 1
        last_sealed_hash = row_hash
        head_hash = row_hash

    valid = first_break is None
    return LedgerChainVerificationResult(
        valid=valid,
        sealed_count=sealed_count,
        unsealed_count=unsealed_count,
        total_events=len(rows),
        head_hash=head_hash,
        first_break=first_break,
    )
