"""BindAuthority — governed bind/commit before policy in-force."""
from __future__ import annotations

from decimal import Decimal

from fastapi import FastAPI
from pydantic import BaseModel

from platforms.common.platform_sdk import GovernedPlatform, spine_health_payload

from .bind_gate import bind_facets, evaluate_bind

app = FastAPI(title="bindauthority", version="0.2.0")
_GOVERNED = GovernedPlatform("bind_authority")

_AUTO_BIND_PREMIUM = Decimal("50000.00")


class BindRequest(BaseModel):
    application_id: str
    premium: str
    limit: str
    currency: str = "USD"
    sanctions_flag: bool = False
    manual_review_flag: bool = False
    account_id: str = "carrier-default"
    policy_id: str = "bind-standard-us"


class BindResponse(BaseModel):
    application_id: str
    decision: str
    bind_score: float
    reason: str | None = None
    crystal_id: str | None = None


@app.get("/healthz")
def healthz() -> dict:
    return spine_health_payload("bind_authority")


@app.get("/readyz")
def readyz() -> dict:
    return healthz()


@app.post("/bind/evaluate", response_model=BindResponse)
def evaluate(request: BindRequest) -> BindResponse:
    premium = Decimal(request.premium)
    limit = Decimal(request.limit)
    result = evaluate_bind(
        application_id=request.application_id,
        premium=premium,
        limit=limit,
        auto_bind_premium=_AUTO_BIND_PREMIUM,
        sanctions_flag=request.sanctions_flag,
        manual_review_flag=request.manual_review_flag,
    )
    facets = bind_facets(
        application_id=request.application_id,
        premium=premium,
        limit=limit,
        currency=request.currency,
        decision=result.decision,
        score=result.score,
    )
    crystal_id = _GOVERNED.govern_operation(
        request.application_id,
        facets,
        decision=result.decision,
        reserve_amount=str(premium),
        account_id=request.account_id,
        policy_id=request.policy_id,
        outcome="bound",
    )
    return BindResponse(
        application_id=request.application_id,
        decision=result.decision,
        bind_score=result.score,
        reason=result.reason,
        crystal_id=crystal_id,
    )
