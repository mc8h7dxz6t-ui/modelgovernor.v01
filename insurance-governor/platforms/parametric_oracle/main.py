"""ParametricOracle — governed parametric trigger with oracle attestation."""
from __future__ import annotations

from decimal import Decimal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from platforms.common.platform_sdk import GovernedPlatform, spine_health_payload

from .trigger_gate import evaluate_trigger, trigger_facets, verify_oracle_attestation

app = FastAPI(title="parametricoracle", version="0.2.0")
_GOVERNED = GovernedPlatform("parametric_oracle")


class TriggerRequest(BaseModel):
    event_id: str
    metric_value: str
    threshold: str
    oracle_source: str
    oracle_payload: str
    oracle_attestation_hash: str
    payout_reserve: str = "0"
    account_id: str = "carrier-default"
    policy_id: str = "parametric-cat-us"


class TriggerResponse(BaseModel):
    event_id: str
    decision: str
    trigger_score: float
    reason: str | None = None
    crystal_id: str | None = None


@app.get("/healthz")
def healthz() -> dict:
    return spine_health_payload("parametric_oracle")


@app.get("/readyz")
def readyz() -> dict:
    return healthz()


@app.post("/trigger/evaluate", response_model=TriggerResponse)
def evaluate(request: TriggerRequest) -> TriggerResponse:
    if not verify_oracle_attestation(
        source=request.oracle_source,
        payload=request.oracle_payload,
        attestation_hash=request.oracle_attestation_hash,
    ):
        raise HTTPException(status_code=422, detail="oracle attestation mismatch")

    metric = Decimal(request.metric_value)
    threshold = Decimal(request.threshold)
    result = evaluate_trigger(
        event_id=request.event_id,
        metric_value=metric,
        threshold=threshold,
        oracle_verified=True,
    )
    facets = trigger_facets(
        event_id=request.event_id,
        metric_value=metric,
        threshold=threshold,
        oracle_source=request.oracle_source,
        attestation_hash=request.oracle_attestation_hash,
        decision=result.decision,
        score=result.score,
    )
    reserve = request.payout_reserve if result.triggered else "0"
    crystal_id = _GOVERNED.govern_operation(
        request.event_id,
        facets,
        decision=result.decision,
        reserve_amount=reserve,
        account_id=request.account_id,
        policy_id=request.policy_id,
        outcome="triggered",
    )
    return TriggerResponse(
        event_id=request.event_id,
        decision=result.decision,
        trigger_score=result.score,
        reason=result.reason,
        crystal_id=crystal_id,
    )
