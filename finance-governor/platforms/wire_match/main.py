"""WireMatch gate API."""
from __future__ import annotations

import hashlib
import logging
import os
from decimal import Decimal

from fastapi import FastAPI
from pydantic import BaseModel

from platforms.common.platform_metrics import get_platform_counters
from platforms.common.platform_observability import mount_platform_observability
from platforms.common.platform_store import append_platform_event

from .semantic_matcher import GOLDEN_RECORD_VERSION, GoldenRecord, evaluate_wire
from .wire_schema import WireRequest

logger = logging.getLogger(__name__)

app = FastAPI(title="wirematch", version="0.2.0")
_COUNTERS = get_platform_counters("wire_match")

_GOLDEN = GoldenRecord(
    beneficiary_name="Revlon Lenders Group",
    beneficiary_account="US12REV001",
    expected_amount=Decimal("7800000.00"),
)

mount_platform_observability(app, platform="wire_match")


class EvaluateResponse(BaseModel):
    wire_id: str
    decision: str
    match_score: float
    reason: str | None = None
    crystal_id: str | None = None


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
        _COUNTERS.increment("wire_sent_below_threshold_total")
    if result.approved:
        _COUNTERS.increment("wire_approved_total")
    else:
        _COUNTERS.increment("wire_held_total")

    facets = {
        "amount": wire.amount,
        "amount_quantum": wire.amount,
        "currency": wire.currency.upper(),
        "beneficiary_hash": hashlib.sha256(wire.beneficiary_account.encode()).hexdigest(),
        "semantic_match_score": result.score,
        "golden_record_version": GOLDEN_RECORD_VERSION,
    }
    crystal_id = _crystallize_if_spine(wire.wire_id, facets, approved=result.approved)
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


def _crystallize_if_spine(operation_id: str, facets: dict, *, approved: bool) -> str | None:
    if os.environ.get("FG_SPINE_ENABLED", "false").lower() != "true":
        return None
    try:
        from platforms.common.spine_adapter import CommitOutcome, SpineAdapter

        adapter = SpineAdapter(platform="wire_match", spine_enabled=True)
        crystal = adapter.crystallize(
            operation_id=operation_id,
            risk_tier="critical",
            facets=facets,
            policy_id="wire-critical-us",
        )
        if approved:
            adapter.commit(
                CommitOutcome(
                    operation_id=operation_id,
                    crystal_id=crystal.crystal_id,
                    facets=facets,
                    outcome="approved",
                    committed_exposure=facets.get("amount", "0"),
                )
            )
        return crystal.crystal_id
    except Exception as exc:
        logger.warning("spine crystallize/commit failed operation=%s: %s", operation_id, exc)
        return None
