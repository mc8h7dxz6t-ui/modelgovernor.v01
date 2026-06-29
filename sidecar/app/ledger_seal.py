"""Tamper-evident hash chaining for ledger_events (enterprise audit trail)."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from .chain_checkpoint import (
    VerifyCheckpoint,
    count_events,
    load_checkpoint,
    save_checkpoint,
    schema_supports_checkpoints,
)

GENESIS_HASH = "0" * 64
EVENTS_TABLE = "ledger_events"
CHECKPOINT_TABLE = "ledger_chain_verify_checkpoints"


def _persist_checkpoint(session: Session, checkpoint: VerifyCheckpoint) -> None:
    save_checkpoint(session, CHECKPOINT_TABLE, checkpoint)
    session.commit()


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
    incremental: bool = False

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "valid": self.valid,
            "sealed_count": self.sealed_count,
            "unsealed_count": self.unsealed_count,
            "total_events": self.total_events,
            "head_hash": self.head_hash,
            "incremental": self.incremental,
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


from spine_core.metadata import normalize_metadata as _normalize_metadata


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
    prev_hash = (
        session.execute(
            text(
                f"""
                SELECT row_hash FROM {EVENTS_TABLE}
                WHERE row_hash IS NOT NULL AND row_hash != :genesis AND event_id < :eid
                ORDER BY event_id DESC
                LIMIT 1
                """
            ),
            {"genesis": GENESIS_HASH, "eid": event_id},
        ).scalar_one_or_none()
        or GENESIS_HASH
    )

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


def head_hash(session: Session) -> str | None:
    if not schema_supports_ledger_seal(session):
        return None
    row = session.execute(
        text(
            f"""
            SELECT row_hash FROM {EVENTS_TABLE}
            WHERE row_hash IS NOT NULL AND row_hash != :genesis
            ORDER BY event_id DESC
            LIMIT 1
            """
        ),
        {"genesis": GENESIS_HASH},
    ).first()
    return row[0] if row else None


@dataclass
class _LedgerVerifyState:
    valid: bool
    sealed_count: int
    unsealed_count: int
    head_hash: str | None
    first_break: LedgerChainBreak | None
    last_event_id: int


def _verify_ledger_rows(
    session: Session,
    *,
    from_event_id: int = 0,
    prior_sealed: int = 0,
) -> _LedgerVerifyState:
    if from_event_id > 0:
        anchor = session.execute(
            text(f"SELECT row_hash FROM {EVENTS_TABLE} WHERE event_id = :event_id"),
            {"event_id": from_event_id},
        ).first()
        if not anchor:
            from_event_id = 0
            prior_sealed = 0
            last_sealed_hash = GENESIS_HASH
        else:
            last_sealed_hash = anchor[0]
    else:
        last_sealed_hash = GENESIS_HASH

    where_clause = "WHERE event_id > :from_event_id" if from_event_id > 0 else ""
    rows = session.execute(
        text(
            f"""
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
            FROM {EVENTS_TABLE}
            {where_clause}
            ORDER BY event_id ASC
            """
        ),
        {"from_event_id": from_event_id} if from_event_id > 0 else {},
    ).mappings().all()

    if from_event_id > 0 and not rows:
        return _LedgerVerifyState(
            valid=True,
            sealed_count=prior_sealed,
            unsealed_count=0,
            head_hash=last_sealed_hash,
            first_break=None,
            last_event_id=from_event_id,
        )

    sealed_count = prior_sealed
    unsealed_count = 0
    head: str | None = last_sealed_hash if last_sealed_hash != GENESIS_HASH else None
    first_break: LedgerChainBreak | None = None
    last_event_id = from_event_id

    for row in rows:
        last_event_id = int(row["event_id"])
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
                event_id=last_event_id,
                reason=f"prev_hash mismatch at event_id={row['event_id']}",
            )
            break

        expected_hash = compute_row_hash(
            event_id=last_event_id,
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
                event_id=last_event_id,
                reason=f"row_hash mismatch at event_id={row['event_id']}",
            )
            break

        sealed_count += 1
        last_sealed_hash = row_hash
        head = row_hash

    return _LedgerVerifyState(
        valid=first_break is None,
        sealed_count=sealed_count,
        unsealed_count=unsealed_count,
        head_hash=head,
        first_break=first_break,
        last_event_id=last_event_id,
    )


def verify_ledger_chain(
    session: Session,
    *,
    incremental: bool = True,
    read_session: Session | None = None,
) -> LedgerChainVerificationResult:
    verify_session = read_session or session

    if not schema_supports_ledger_seal(verify_session):
        return LedgerChainVerificationResult(
            valid=False,
            sealed_count=0,
            unsealed_count=0,
            total_events=0,
            head_hash=None,
            first_break=LedgerChainBreak(event_id=0, reason="seal_schema_unavailable"),
        )

    total_events = count_events(verify_session, EVENTS_TABLE)
    if total_events == 0:
        return LedgerChainVerificationResult(
            valid=True, sealed_count=0, unsealed_count=0, total_events=0, head_hash=None
        )

    current_head = head_hash(verify_session)
    checkpoints_enabled = schema_supports_checkpoints(verify_session, CHECKPOINT_TABLE)

    if incremental and checkpoints_enabled:
        checkpoint = load_checkpoint(verify_session, CHECKPOINT_TABLE)
        if checkpoint and current_head and checkpoint.verified_head_hash == current_head:
            if total_events == checkpoint.total_events:
                return LedgerChainVerificationResult(
                    valid=True,
                    sealed_count=checkpoint.sealed_count,
                    unsealed_count=0,
                    total_events=total_events,
                    head_hash=current_head,
                    incremental=True,
                )

        if checkpoint and current_head:
            tail_result = _verify_ledger_rows(
                verify_session,
                from_event_id=checkpoint.last_verified_event_id,
                prior_sealed=checkpoint.sealed_count,
            )
            if tail_result.valid and tail_result.head_hash:
                _persist_checkpoint(
                    session,
                    VerifyCheckpoint(
                        last_verified_event_id=tail_result.last_event_id,
                        verified_head_hash=tail_result.head_hash,
                        sealed_count=tail_result.sealed_count,
                        total_events=total_events,
                    ),
                )
                return LedgerChainVerificationResult(
                    valid=True,
                    sealed_count=tail_result.sealed_count,
                    unsealed_count=tail_result.unsealed_count,
                    total_events=total_events,
                    head_hash=tail_result.head_hash,
                    incremental=True,
                )

    full = _verify_ledger_rows(verify_session)
    result = LedgerChainVerificationResult(
        valid=full.valid,
        sealed_count=full.sealed_count,
        unsealed_count=full.unsealed_count,
        total_events=total_events,
        head_hash=full.head_hash,
        first_break=full.first_break,
        incremental=False,
    )
    if result.valid and incremental and checkpoints_enabled and result.head_hash:
        _persist_checkpoint(
            session,
            VerifyCheckpoint(
                last_verified_event_id=full.last_event_id,
                verified_head_hash=result.head_hash,
                sealed_count=result.sealed_count,
                total_events=total_events,
            ),
        )
    return result
