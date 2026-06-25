"""ClaimGate — governed payout gate (standalone or spine-connected)."""
from __future__ import annotations

from decimal import Decimal

from fastapi import FastAPI
from pydantic import BaseModel

from platforms.common.platform_sdk import GovernedPlatform, spine_health_payload

from .payout_gate import evaluate_payout, payout_facets

app = FastAPI(title="claimgate", version="0.2.0")
_GOVERNED = GovernedPlatform("claim_gate")

_POLICY_LIMIT = Decimal("5000000.00")
_AUTO_APPROVE = Decimal("250000.00")


class PayoutRequest(BaseModel):
    claim_id: str
    payout_amount: str
    currency: str = "USD"
    siu_flag: bool = False
    account_id: str = "carrier-default"
    policy_id: str = "claim-high-us"


class PayoutResponse(BaseModel):
    claim_id: str
    decision: str
    gate_score: float
    reason: str | None = None
    crystal_id: str | None = None


@app.get("/healthz")
def healthz() -> dict:
    return spine_health_payload("claim_gate")


@app.get("/readyz")
def readyz() -> dict:
    return healthz()


@app.post("/claim/evaluate", response_model=PayoutResponse)
def evaluate(request: PayoutRequest) -> PayoutResponse:
    amount = Decimal(request.payout_amount)
    result = evaluate_payout(
        claim_id=request.claim_id,
        payout_amount=amount,
        policy_limit=_POLICY_LIMIT,
        auto_approve_limit=_AUTO_APPROVE,
        siu_flag=request.siu_flag,
    )
    facets = payout_facets(
        claim_id=request.claim_id,
        payout_amount=amount,
        currency=request.currency,
        decision=result.decision,
        score=result.score,
    )
    crystal_id = _GOVERNED.govern_operation(
        request.claim_id,
        facets,
        decision=result.decision,
        reserve_amount=str(amount),
        account_id=request.account_id,
        policy_id=request.policy_id,
        outcome="paid",
    )
    return PayoutResponse(
        claim_id=request.claim_id,
        decision=result.decision,
        gate_score=result.score,
        reason=result.reason,
        crystal_id=crystal_id,
    )
