"""Hash chaining for claim_events — tamper-evident audit trail."""
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
EVENTS_TABLE = "claim_events"
CHECKPOINT_TABLE = "claim_chain_verify_checkpoints"


def _persist_checkpoint(session: Session, checkpoint: VerifyCheckpoint) -> None:
    save_checkpoint(session, CHECKPOINT_TABLE, checkpoint)
    session.commit()


@dataclass(frozen=True)
class ClaimChainBreak:
    event_id: int
    reason: str


@dataclass
class ClaimChainVerificationResult:
    valid: bool
    sealed_count: int
    unsealed_count: int
    total_events: int
    head_hash: str | None
    first_break: ClaimChainBreak | None = None
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
    operation_id: str,
    crystal_id: str | None,
    account_id: str,
    event_type: str,
    reserve_delta: str,
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
            "reserve_delta": reserve_delta,
            "metadata": metadata,
            "prev_hash": prev_hash,
            "recorded_at": recorded_at,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(body.encode()).hexdigest()


def head_hash(session: Session) -> str | None:
    if not schema_supports_claim_seal(session):
        return None
    row = session.execute(text(f"SELECT row_hash FROM {EVENTS_TABLE} ORDER BY event_id DESC LIMIT 1")).first()
    return row[0] if row else None


def schema_supports_claim_seal(session: Session) -> bool:
    dialect = session.bind.dialect.name
    if dialect == "postgresql":
        row = session.execute(
            text(
                """
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = 'claim_events' AND column_name = 'row_hash'
                """
            )
        ).first()
        return row is not None
    if dialect == "sqlite":
        rows = session.execute(text("PRAGMA table_info(claim_events)")).fetchall()
        return any(str(column[1]) == "row_hash" for column in rows)
    return False


def _fetch_event_rows(session: Session, *, from_event_id: int | None = None) -> list[Any]:
    if from_event_id is None:
        sql = f"""
            SELECT event_id, operation_id, crystal_id, account_id, event_type,
                   reserve_delta, metadata, prev_hash, row_hash, recorded_at
            FROM {EVENTS_TABLE} ORDER BY event_id ASC
        """
        return session.execute(text(sql)).mappings().all()
    sql = f"""
        SELECT event_id, operation_id, crystal_id, account_id, event_type,
               reserve_delta, metadata, prev_hash, row_hash, recorded_at
        FROM {EVENTS_TABLE}
        WHERE event_id > :from_event_id
        ORDER BY event_id ASC
    """
    return session.execute(text(sql), {"from_event_id": from_event_id}).mappings().all()


def _expected_prev_hash(session: Session, last_verified_event_id: int) -> str | None:
    if last_verified_event_id <= 0:
        return GENESIS_HASH
    row = session.execute(
        text(f"SELECT row_hash FROM {EVENTS_TABLE} WHERE event_id = :event_id"),
        {"event_id": last_verified_event_id},
    ).first()
    return row[0] if row else None


def _verify_rows(
    rows: list[Any],
    *,
    expected_prev: str,
    prior_sealed: int,
) -> tuple[int, int, ClaimChainBreak | None, str | None]:
    from decimal import Decimal

    from .currency import quantize_money

    sealed = prior_sealed
    unsealed = 0
    first_break: ClaimChainBreak | None = None
    expected = expected_prev
    tail_head: str | None = expected_prev if expected_prev != GENESIS_HASH else None

    for row in rows:
        event_id = int(row["event_id"])
        prev = row["prev_hash"] or GENESIS_HASH
        if prev != expected:
            if first_break is None:
                first_break = ClaimChainBreak(event_id=event_id, reason="prev_hash mismatch")
        meta = _normalize_metadata(row["metadata"])
        recorded = row["recorded_at"]
        if hasattr(recorded, "isoformat"):
            recorded = recorded.isoformat()
        else:
            recorded = str(recorded)
        reserve_delta = str(quantize_money(Decimal(str(row["reserve_delta"]))))
        computed = compute_row_hash(
            event_id=event_id,
            operation_id=row["operation_id"],
            crystal_id=row["crystal_id"],
            account_id=row["account_id"],
            event_type=row["event_type"],
            reserve_delta=reserve_delta,
            metadata=meta,
            prev_hash=prev,
            recorded_at=recorded,
        )
        stored = row["row_hash"]
        if stored == computed:
            sealed += 1
        else:
            unsealed += 1
            if first_break is None:
                first_break = ClaimChainBreak(event_id=event_id, reason="row_hash mismatch")
        expected = stored
        tail_head = stored

    return sealed, unsealed, first_break, tail_head


def verify_claim_chain(
    session: Session,
    *,
    incremental: bool = True,
    read_session: Session | None = None,
) -> ClaimChainVerificationResult:
    verify_session = read_session or session

    if not schema_supports_claim_seal(verify_session):
        return ClaimChainVerificationResult(
            valid=False,
            sealed_count=0,
            unsealed_count=0,
            total_events=0,
            head_hash=None,
            first_break=ClaimChainBreak(event_id=0, reason="seal_schema_unavailable"),
        )

    total_events = count_events(verify_session, EVENTS_TABLE)
    if total_events == 0:
        return ClaimChainVerificationResult(
            valid=True, sealed_count=0, unsealed_count=0, total_events=0, head_hash=None
        )

    current_head = head_hash(verify_session)
    checkpoints_enabled = schema_supports_checkpoints(verify_session, CHECKPOINT_TABLE)

    if incremental and checkpoints_enabled:
        checkpoint = load_checkpoint(verify_session, CHECKPOINT_TABLE)
        if checkpoint and current_head and checkpoint.verified_head_hash == current_head:
            return ClaimChainVerificationResult(
                valid=True,
                sealed_count=checkpoint.sealed_count,
                unsealed_count=0,
                total_events=total_events,
                head_hash=current_head,
                incremental=True,
            )

        if checkpoint and current_head:
            expected_prev = _expected_prev_hash(verify_session, checkpoint.last_verified_event_id)
            if expected_prev is not None:
                tail_rows = _fetch_event_rows(verify_session, from_event_id=checkpoint.last_verified_event_id)
                if not tail_rows:
                    return ClaimChainVerificationResult(
                        valid=True,
                        sealed_count=checkpoint.sealed_count,
                        unsealed_count=0,
                        total_events=total_events,
                        head_hash=current_head,
                        incremental=True,
                    )
                sealed, unsealed, first_break, tail_head = _verify_rows(
                    tail_rows,
                    expected_prev=expected_prev,
                    prior_sealed=checkpoint.sealed_count,
                )
                if first_break is None and unsealed == 0 and tail_head:
                    _persist_checkpoint(
                        session,
                        VerifyCheckpoint(
                            last_verified_event_id=int(tail_rows[-1]["event_id"]),
                            verified_head_hash=tail_head,
                            sealed_count=sealed,
                            total_events=total_events,
                        ),
                    )
                    return ClaimChainVerificationResult(
                        valid=True,
                        sealed_count=sealed,
                        unsealed_count=0,
                        total_events=total_events,
                        head_hash=tail_head,
                        incremental=True,
                    )

    rows = _fetch_event_rows(verify_session)
    sealed, unsealed, first_break, tail_head = _verify_rows(rows, expected_prev=GENESIS_HASH, prior_sealed=0)
    result = ClaimChainVerificationResult(
        valid=first_break is None and unsealed == 0,
        sealed_count=sealed,
        unsealed_count=unsealed,
        total_events=len(rows),
        head_hash=rows[-1]["row_hash"] if rows else None,
        first_break=first_break,
        incremental=False,
    )
    if result.valid and incremental and checkpoints_enabled and result.head_hash and rows:
        _persist_checkpoint(
            session,
            VerifyCheckpoint(
                last_verified_event_id=int(rows[-1]["event_id"]),
                verified_head_hash=result.head_hash,
                sealed_count=result.sealed_count,
                total_events=result.total_events,
            ),
        )
    return result
