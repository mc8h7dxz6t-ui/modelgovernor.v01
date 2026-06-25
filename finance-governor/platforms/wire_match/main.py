"""WireMatch gate API."""
from __future__ import annotations

import os
from decimal import Decimal

from fastapi import FastAPI
from pydantic import BaseModel

from .semantic_matcher import GoldenRecord, evaluate_wire
from .wire_schema import WireRequest

app = FastAPI(title="wirematch", version="0.1.0")

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


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok"}


@app.post("/wire/evaluate", response_model=EvaluateResponse)
def evaluate(wire: WireRequest) -> EvaluateResponse:
    amount = Decimal(wire.amount)
    result = evaluate_wire(
        beneficiary_name=wire.beneficiary_name,
        beneficiary_account=wire.beneficiary_account,
        amount=amount,
        golden=_GOLDEN,
    )
    facets = {
        "amount": wire.amount,
        "currency": wire.currency,
        "beneficiary_hash": wire.beneficiary_account,
        "semantic_score": result.score,
    }
    crystal_id = _crystallize_if_spine(wire.wire_id, facets, approved=result.approved)

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
    except Exception:
        return None
