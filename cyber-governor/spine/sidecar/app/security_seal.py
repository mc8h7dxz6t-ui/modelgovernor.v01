"""Hash chaining for security_events."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

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


def schema_supports_security_seal(session) -> bool:
    from sqlalchemy import text

    dialect = session.bind.dialect.name
    if dialect == "postgresql":
        row = session.execute(
            text(
                """
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'security_events' AND column_name = 'row_hash'
                """
            )
        ).first()
        return row is not None
    if dialect == "sqlite":
        rows = session.execute(text("PRAGMA table_info(security_events)")).fetchall()
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
        text("SELECT row_hash FROM security_events ORDER BY event_id DESC LIMIT 1")
    ).first()
    return row[0] if row else None


def verify_security_chain(session) -> SecurityChainVerificationResult:
    from decimal import Decimal

    from sqlalchemy import text

    from .currency import quantize_money

    if not schema_supports_security_seal(session):
        return SecurityChainVerificationResult(
            valid=True,
            sealed_count=0,
            unsealed_count=0,
            total_events=0,
            head_hash=None,
        )

    rows = session.execute(
        text(
            """
            SELECT event_id, operation_id, crystal_id, account_id, event_type,
                   exposure_delta, metadata, recorded_at, prev_hash, row_hash
            FROM security_events
            ORDER BY event_id ASC
            """
        )
    ).mappings().all()

    last_sealed_hash = GENESIS_HASH
    sealed_count = 0
    unsealed_count = 0
    head_hash_value: str | None = None
    first_break: SecurityChainBreak | None = None

    for row in rows:
        row_hash = row["row_hash"]
        if row_hash is None:
            unsealed_count += 1
            continue

        metadata = _normalize_metadata(row["metadata"])
        exposure_delta = str(quantize_money(Decimal(str(row["exposure_delta"]))))
        recorded_at = str(row["recorded_at"])
        prev_hash = row["prev_hash"] or GENESIS_HASH

        if prev_hash != last_sealed_hash:
            first_break = SecurityChainBreak(
                event_id=int(row["event_id"]),
                reason=f"prev_hash mismatch at event_id={row['event_id']}",
            )
            break

        expected_hash = compute_row_hash(
            event_id=int(row["event_id"]),
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
            first_break = SecurityChainBreak(
                event_id=int(row["event_id"]),
                reason=f"row_hash mismatch at event_id={row['event_id']}",
            )
            break

        sealed_count += 1
        last_sealed_hash = row_hash
        head_hash_value = row_hash

    return SecurityChainVerificationResult(
        valid=first_break is None,
        sealed_count=sealed_count,
        unsealed_count=unsealed_count,
        total_events=len(rows),
        head_hash=head_hash_value,
        first_break=first_break,
    )
