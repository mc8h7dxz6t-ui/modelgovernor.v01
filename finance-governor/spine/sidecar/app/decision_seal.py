"""Hash chaining for decision_events — tamper-evident audit trail."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
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
EVENTS_TABLE = "decision_events"
CHECKPOINT_TABLE = "decision_chain_verify_checkpoints"


def _persist_checkpoint(session: Session, checkpoint: VerifyCheckpoint) -> None:
    save_checkpoint(session, CHECKPOINT_TABLE, checkpoint)
    session.commit()


@dataclass(frozen=True)
class DecisionChainBreak:
    event_id: int
    reason: str


@dataclass
class DecisionChainVerificationResult:
    valid: bool
    sealed_count: int
    unsealed_count: int
    total_events: int
    head_hash: str | None
    first_break: DecisionChainBreak | None = None
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


def head_hash(session: Session) -> str | None:
    row = session.execute(
        text(
            """
            SELECT row_hash FROM decision_events
            WHERE row_hash IS NOT NULL AND row_hash != :genesis
            ORDER BY event_id DESC
            LIMIT 1
            """
        ),
        {"genesis": GENESIS_HASH},
    ).first()
    return row[0] if row else None


from spine_core.metadata import normalize_metadata as _normalize_metadata


def schema_supports_decision_seal(session: Session) -> bool:
    dialect = session.bind.dialect.name
    if dialect == "postgresql":
        row = session.execute(
            text(
                """
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = 'decision_events' AND column_name = 'row_hash'
                """
            )
        ).first()
        return row is not None
    if dialect == "sqlite":
        rows = session.execute(text("PRAGMA table_info(decision_events)")).fetchall()
        return any(str(column[1]) == "row_hash" for column in rows)
    return False


def seal_decision_event(
    session: Session,
    *,
    event_id: int,
    operation_id: str,
    crystal_id: str | None,
    account_id: str,
    event_type: str,
    exposure_delta: str,
    metadata: dict[str, Any],
    recorded_at: str,
) -> tuple[str, str]:
    prev_hash = (
        session.execute(
            text(
                """
                SELECT row_hash FROM decision_events
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
        operation_id=operation_id,
        crystal_id=crystal_id,
        account_id=account_id,
        event_type=event_type,
        exposure_delta=exposure_delta,
        metadata=metadata,
        prev_hash=prev_hash,
        recorded_at=recorded_at,
    )
    session.execute(
        text(
            """
            UPDATE decision_events
            SET prev_hash = :prev_hash, row_hash = :row_hash
            WHERE event_id = :event_id
            """
        ),
        {"prev_hash": prev_hash, "row_hash": row_hash, "event_id": event_id},
    )
    return prev_hash, row_hash


def append_decision_event(
    session: Session,
    *,
    operation_id: str,
    crystal_id: str | None,
    account_id: str,
    event_type: str,
    exposure_delta: Decimal,
    metadata: dict[str, Any],
) -> int:
    from spine_core.chain_advisory_lock import chain_append_lock
    from spine_core.config import CHAIN_APPEND_LOCK_KEYS, GovernorDomain

    with chain_append_lock(session, lock_key=CHAIN_APPEND_LOCK_KEYS[GovernorDomain.FINANCE]):
        return _append_decision_event_locked(
            session,
            operation_id=operation_id,
            crystal_id=crystal_id,
            account_id=account_id,
            event_type=event_type,
            exposure_delta=exposure_delta,
            metadata=metadata,
        )


def _append_decision_event_locked(
    session: Session,
    *,
    operation_id: str,
    crystal_id: str | None,
    account_id: str,
    event_type: str,
    exposure_delta: Decimal,
    metadata: dict[str, Any],
) -> int:
    from .currency import quantize_money

    if not schema_supports_decision_seal(session):
        raise RuntimeError("decision_events seal columns unavailable")

    prev = head_hash(session) or GENESIS_HASH
    now = datetime.now(timezone.utc)
    meta_sql = ":meta" if session.bind.dialect.name == "sqlite" else "CAST(:meta AS jsonb)"
    recorded_at_param = now.isoformat() if session.bind.dialect.name == "sqlite" else now
    amount = str(quantize_money(exposure_delta))

    event_id = session.execute(
        text(
            f"""
            INSERT INTO decision_events (
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
            "exposure_delta": amount,
            "meta": json.dumps(metadata, sort_keys=True),
            "prev_hash": prev,
            "placeholder": prev,
            "recorded_at": recorded_at_param,
        },
    ).scalar_one()

    dialect = session.bind.dialect.name
    recorded_expr = "recorded_at::text" if dialect == "postgresql" else "recorded_at"
    row = session.execute(
        text(f"SELECT {recorded_expr} AS recorded_at FROM decision_events WHERE event_id = :eid"),
        {"eid": event_id},
    ).mappings().first()
    recorded_at = str(row["recorded_at"]) if row else now.isoformat()

    seal_decision_event(
        session,
        event_id=int(event_id),
        operation_id=operation_id,
        crystal_id=crystal_id,
        account_id=account_id,
        event_type=event_type,
        exposure_delta=amount,
        metadata=metadata,
        recorded_at=recorded_at,
    )
    return int(event_id)


def verify_decision_chain(
    session: Session,
    *,
    incremental: bool = True,
    read_session: Session | None = None,
) -> DecisionChainVerificationResult:
    from .currency import quantize_money

    verify_session = read_session or session

    if not schema_supports_decision_seal(verify_session):
        return DecisionChainVerificationResult(
            valid=False,
            sealed_count=0,
            unsealed_count=0,
            total_events=0,
            head_hash=None,
            first_break=DecisionChainBreak(event_id=0, reason="seal_schema_unavailable"),
        )

    total_events = count_events(verify_session, EVENTS_TABLE)
    if total_events == 0:
        return DecisionChainVerificationResult(
            valid=True, sealed_count=0, unsealed_count=0, total_events=0, head_hash=None
        )

    current_head = head_hash(verify_session)
    checkpoints_enabled = schema_supports_checkpoints(verify_session, CHECKPOINT_TABLE)

    if incremental and checkpoints_enabled:
        checkpoint = load_checkpoint(verify_session, CHECKPOINT_TABLE)
        if checkpoint and current_head and checkpoint.verified_head_hash == current_head:
            if total_events == checkpoint.total_events:
                return DecisionChainVerificationResult(
                    valid=True,
                    sealed_count=checkpoint.sealed_count,
                    unsealed_count=0,
                    total_events=total_events,
                    head_hash=current_head,
                    incremental=True,
                )

        if checkpoint and current_head:
            tail_result = _verify_decision_rows(
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
                return DecisionChainVerificationResult(
                    valid=True,
                    sealed_count=tail_result.sealed_count,
                    unsealed_count=tail_result.unsealed_count,
                    total_events=total_events,
                    head_hash=tail_result.head_hash,
                    incremental=True,
                )

    full = _verify_decision_rows(verify_session)
    result = DecisionChainVerificationResult(
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


@dataclass
class _DecisionVerifyState:
    valid: bool
    sealed_count: int
    unsealed_count: int
    head_hash: str | None
    first_break: DecisionChainBreak | None
    last_event_id: int


def _verify_decision_rows(
    session: Session,
    *,
    from_event_id: int = 0,
    prior_sealed: int = 0,
) -> _DecisionVerifyState:
    from .currency import quantize_money

    dialect = session.bind.dialect.name
    recorded_col = (
        "recorded_at::text AS recorded_at" if dialect == "postgresql" else "recorded_at"
    )
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
                operation_id,
                crystal_id,
                account_id,
                event_type,
                exposure_delta,
                metadata,
                {recorded_col},
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
        return _DecisionVerifyState(
            valid=True,
            sealed_count=prior_sealed,
            unsealed_count=0,
            head_hash=last_sealed_hash if last_sealed_hash != GENESIS_HASH else None,
            first_break=None,
            last_event_id=from_event_id,
        )

    sealed_count = prior_sealed
    unsealed_count = 0
    head: str | None = last_sealed_hash if last_sealed_hash != GENESIS_HASH else None
    first_break: DecisionChainBreak | None = None
    last_event_id = from_event_id

    for row in rows:
        last_event_id = int(row["event_id"])
        row_hash = row["row_hash"]
        if row_hash is None or row_hash == GENESIS_HASH:
            unsealed_count += 1
            continue

        metadata = _normalize_metadata(row["metadata"])
        exposure_delta = str(quantize_money(Decimal(str(row["exposure_delta"]))))
        recorded_at = str(row["recorded_at"])
        prev_hash = row["prev_hash"] or GENESIS_HASH

        if prev_hash != last_sealed_hash:
            first_break = DecisionChainBreak(
                event_id=last_event_id,
                reason=f"prev_hash mismatch at event_id={row['event_id']}",
            )
            break

        expected_hash = compute_row_hash(
            event_id=last_event_id,
            operation_id=row["operation_id"],
            crystal_id=row["crystal_id"],
            account_id=row["account_id"],
            event_type=row["event_type"],
            exposure_delta=exposure_delta,
            metadata=metadata,
            prev_hash=prev_hash,
            recorded_at=recorded_at,
        )
        if row_hash != expected_hash:
            first_break = DecisionChainBreak(
                event_id=last_event_id,
                reason=f"row_hash mismatch at event_id={row['event_id']}",
            )
            break

        sealed_count += 1
        last_sealed_hash = row_hash
        head = row_hash

    return _DecisionVerifyState(
        valid=first_break is None,
        sealed_count=sealed_count,
        unsealed_count=unsealed_count,
        head_hash=head,
        first_break=first_break,
        last_event_id=last_event_id,
    )
