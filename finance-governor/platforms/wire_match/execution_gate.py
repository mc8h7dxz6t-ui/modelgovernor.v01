"""WireMatch execution gate — reserve → semantic gate → send/settle."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from platforms.common.event_store import AppendOnlyEventStore
from platforms.common.mesh_guard import get_mesh_guard
from platforms.common.platform_metrics import get_platform_metrics

from .semantic_matcher import GoldenRecord, MatchResult, evaluate_wire

_events = AppendOnlyEventStore()
_sent_idempotency: set[str] = set()
_MIN_SEMANTIC_SCORE = 0.6


@dataclass(frozen=True)
class GateDecision:
    wire_id: str
    decision: str
    match_score: float
    reason: str | None = None
    idempotency_key: str | None = None


def get_wire_event_store() -> AppendOnlyEventStore:
    return _events


def evaluate_and_gate(
    *,
    wire_id: str,
    beneficiary_name: str,
    beneficiary_account: str,
    amount: Decimal,
    golden: GoldenRecord,
    idempotency_key: str | None = None,
    min_semantic_score: float = _MIN_SEMANTIC_SCORE,
) -> GateDecision:
    metrics = get_platform_metrics()
    mesh_ok, mesh_reason = get_mesh_guard().allows_wire_send()
    if not mesh_ok:
        metrics.increment("wire_held_total")
        _events.append(
            platform="wire_match",
            event_type="HELD",
            operation_id=wire_id,
            payload={"reason": mesh_reason, "mesh_block": True},
        )
        return GateDecision(wire_id=wire_id, decision="HELD", match_score=0.0, reason=mesh_reason)

    result = evaluate_wire(
        beneficiary_name=beneficiary_name,
        beneficiary_account=beneficiary_account,
        amount=amount,
        golden=golden,
        min_semantic_score=min_semantic_score,
    )
    if not result.approved:
        metrics.increment("wire_held_total")
        _events.append(
            platform="wire_match",
            event_type="HELD",
            operation_id=wire_id,
            payload={"reason": result.reason, "score": result.score},
        )
        return GateDecision(
            wire_id=wire_id,
            decision="HELD",
            match_score=result.score,
            reason=result.reason,
            idempotency_key=idempotency_key,
        )

    return GateDecision(
        wire_id=wire_id,
        decision="APPROVED",
        match_score=result.score,
        idempotency_key=idempotency_key,
    )


def send_wire(
    decision: GateDecision,
    *,
    amount: Decimal,
    min_semantic_score: float = _MIN_SEMANTIC_SCORE,
) -> dict:
    """Pre-rail send gate — blocks below-threshold or duplicate sends."""
    metrics = get_platform_metrics()
    key = decision.idempotency_key or decision.wire_id

    if key in _sent_idempotency:
        metrics.increment("wire_duplicate_idempotency_total")
        return {"status": "DUPLICATE", "wire_id": decision.wire_id, "idempotency_key": key}

    if decision.decision != "APPROVED":
        if decision.match_score < min_semantic_score:
            metrics.increment("wire_sent_below_threshold_total")
        metrics.increment("wire_held_total")
        return {"status": "HELD", "wire_id": decision.wire_id, "reason": decision.reason}

    _sent_idempotency.add(key)
    _events.append(
        platform="wire_match",
        event_type="WIRE_SENT",
        operation_id=decision.wire_id,
        payload={"amount": str(amount), "score": decision.match_score, "idempotency_key": key},
    )
    return {"status": "SENT", "wire_id": decision.wire_id, "idempotency_key": key}
