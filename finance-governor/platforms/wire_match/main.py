"""WireMatch gate API."""
from __future__ import annotations

import hashlib
import logging
from decimal import Decimal

from fastapi import FastAPI
from pydantic import BaseModel

from platforms.common.platform_configs import WIRE_MATCH_CONFIG
from platforms.common.platform_sdk import create_platform_app, increment_invariant, spine_adapter_for
from platforms.common.platform_store import append_platform_event
from platforms.common.spine_helpers import crystallize_and_commit

from .semantic_matcher import GOLDEN_RECORD_VERSION, GoldenRecord, evaluate_wire
from .wire_schema import WireRequest

logger = logging.getLogger(__name__)

CONFIG = WIRE_MATCH_CONFIG
app = create_platform_app(CONFIG)
adapter = spine_adapter_for(CONFIG)

_GOLDEN = GoldenRecord(
    beneficiary_name="Revlon Lenders Group",
    beneficiary_account="US12REV001",
    expected_amount=Decimal("7800000.00"),
)


class EvaluateResponse(BaseModel):
    wire_id: str
    decision: str
    match_score: float
    reason: str | None = None
    crystal_id: str | None = None


@app.get("/events")
def list_events(limit: int = 20) -> list:
    from platforms.common.platform_store import list_platform_events

    return list_platform_events("wire_match", limit=limit)


@app.post("/wire/evaluate", response_model=EvaluateResponse)
def evaluate(wire: WireRequest) -> EvaluateResponse:
    amount = Decimal(wire.amount)
    result = evaluate_wire(
        beneficiary_name=wire.beneficiary_name,
        beneficiary_account=wire.beneficiary_account,
        amount=amount,
        golden=_GOLDEN,
    )
    if result.approved and result.score < 0.6:
        increment_invariant(CONFIG.name, "wire_sent_below_threshold_total")
    if result.approved:
        increment_invariant(CONFIG.name, "wire_approved_total")
    else:
        increment_invariant(CONFIG.name, "wire_held_total")

    facets = {
        "amount": wire.amount,
        "amount_quantum": wire.amount,
        "currency": wire.currency.upper(),
        "beneficiary_hash": hashlib.sha256(wire.beneficiary_account.encode()).hexdigest(),
        "semantic_match_score": result.score,
        "golden_record_version": GOLDEN_RECORD_VERSION,
    }
    crystal_id = None
    if result.approved:
        crystal_id = crystallize_and_commit(
            CONFIG,
            wire.wire_id,
            facets,
            committed_exposure=wire.amount,
            outcome="approved",
        )
    else:
        crystal_id = crystallize_and_commit(
            CONFIG,
            wire.wire_id,
            facets,
            committed_exposure="0",
            outcome="held",
        )

    append_platform_event(
        "wire_match",
        "APPROVED" if result.approved else "HELD",
        wire.wire_id,
        {"reason": result.reason, "score": result.score},
    )

    return EvaluateResponse(
        wire_id=wire.wire_id,
        decision="APPROVED" if result.approved else "HELD",
        match_score=result.score,
        reason=result.reason,
        crystal_id=crystal_id,
    )
