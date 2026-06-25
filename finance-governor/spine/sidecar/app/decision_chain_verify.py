"""Tamper-evident verification for decision_events hash chain."""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.orm import Session

from .currency import quantize_money
from .decision_seal import GENESIS_HASH, compute_row_hash


@dataclass(frozen=True)
class ChainBreak:
    event_id: int
    reason: str


@dataclass
class DecisionChainVerificationResult:
    valid: bool
    sealed_count: int
    unsealed_count: int
    total_events: int
    head_hash: str | None
    first_break: ChainBreak | None = None

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
        return parsed if isinstance(parsed, dict) else {}
    return {}


def verify_decision_chain(session: Session) -> DecisionChainVerificationResult:
    rows = session.execute(
        text(
            """
            SELECT event_id, operation_id, crystal_id, account_id, event_type,
                   exposure_delta, metadata, prev_hash, row_hash, recorded_at
            FROM decision_events
            ORDER BY event_id ASC
            """
        )
    ).mappings().all()

    last_sealed_hash = GENESIS_HASH
    sealed_count = 0
    unsealed_count = 0
    head_hash: str | None = None
    first_break: ChainBreak | None = None

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
            first_break = ChainBreak(
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
            first_break = ChainBreak(
                event_id=int(row["event_id"]),
                reason=f"row_hash mismatch at event_id={row['event_id']}",
            )
            break

        sealed_count += 1
        last_sealed_hash = row_hash
        head_hash = row_hash

    return DecisionChainVerificationResult(
        valid=first_break is None,
        sealed_count=sealed_count,
        unsealed_count=unsealed_count,
        total_events=len(rows),
        head_hash=head_hash,
        first_break=first_break,
    )
