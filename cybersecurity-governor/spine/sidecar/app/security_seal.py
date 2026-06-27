"""Hash chaining for security_events — tamper-evident audit trail."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

GENESIS_HASH = "0" * 64


@dataclass(frozen=True)
class SecurityChainBreak:
    event_id: int
    reason: str


@dataclass
class SecurityChainVerificationResult:
    valid: bool
    sealed_count: int
    unsealed_count: int
    total_events: int
    head_hash: str | None
    first_break: SecurityChainBreak | None = None

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
    if not schema_supports_security_seal(session):
        return None
    row = session.execute(text("SELECT row_hash FROM security_events ORDER BY event_id DESC LIMIT 1")).first()
    return row[0] if row else None


def schema_supports_security_seal(session: Session) -> bool:
    dialect = session.bind.dialect.name
    if dialect == "postgresql":
        row = session.execute(
            text(
                """
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = 'security_events' AND column_name = 'row_hash'
                """
            )
        ).first()
        return row is not None
    if dialect == "sqlite":
        rows = session.execute(text("PRAGMA table_info(security_events)")).fetchall()
        return any(str(column[1]) == "row_hash" for column in rows)
    return False


def verify_security_chain(session: Session) -> SecurityChainVerificationResult:
    if not schema_supports_security_seal(session):
        return SecurityChainVerificationResult(
            valid=False,
            sealed_count=0,
            unsealed_count=0,
            total_events=0,
            head_hash=None,
            first_break=SecurityChainBreak(event_id=0, reason="seal_schema_unavailable"),
        )

    rows = session.execute(
        text(
            """
            SELECT event_id, operation_id, crystal_id, account_id, event_type,
                   reserve_delta, metadata, prev_hash, row_hash, recorded_at
            FROM security_events ORDER BY event_id ASC
            """
        )
    ).mappings().all()

    if not rows:
        return SecurityChainVerificationResult(valid=True, sealed_count=0, unsealed_count=0, total_events=0, head_hash=None)

    expected_prev = GENESIS_HASH
    sealed = 0
    unsealed = 0
    first_break: SecurityChainBreak | None = None

    for row in rows:
        event_id = int(row["event_id"])
        prev = row["prev_hash"] or GENESIS_HASH
        if prev != expected_prev:
            if first_break is None:
                first_break = SecurityChainBreak(event_id=event_id, reason="prev_hash mismatch")
        meta = _normalize_metadata(row["metadata"])
        recorded = row["recorded_at"]
        if hasattr(recorded, "isoformat"):
            recorded = recorded.isoformat()
        else:
            recorded = str(recorded)
        from decimal import Decimal

        from .currency import quantize_money

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
                first_break = SecurityChainBreak(event_id=event_id, reason="row_hash mismatch")
        expected_prev = stored

    return SecurityChainVerificationResult(
        valid=first_break is None and unsealed == 0,
        sealed_count=sealed,
        unsealed_count=unsealed,
        total_events=len(rows),
        head_hash=rows[-1]["row_hash"],
        first_break=first_break,
    )
