"""ClaimGate — governed payout gate (standalone or spine-connected)."""
from __future__ import annotations

import os
from decimal import Decimal

from fastapi import FastAPI
from pydantic import BaseModel, Field

from .payout_gate import evaluate_payout, payout_facets

app = FastAPI(title="claimgate", version="0.1.0")

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
    spine = os.environ.get("IG_SPINE_ENABLED", "false").lower() == "true"
    return {"status": "ok", "spine_enabled": spine}


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
    crystal_id = _govern_payout(
        request.claim_id,
        facets,
        approved=result.approved,
        amount=amount,
        account_id=request.account_id,
        policy_id=request.policy_id,
    )
    return PayoutResponse(
        claim_id=request.claim_id,
        decision=result.decision,
        gate_score=result.score,
        reason=result.reason,
        crystal_id=crystal_id,
    )


def _govern_payout(
    claim_id: str,
    facets: dict,
    *,
    approved: bool,
    amount: Decimal,
    account_id: str,
    policy_id: str,
) -> str | None:
    try:
        from platforms.common.spine_adapter import CommitOutcome, SpineAdapter

        adapter = SpineAdapter(
            platform="claim_gate",
            spine_enabled=os.environ.get("IG_SPINE_ENABLED", "false").lower() == "true",
        )
        crystal = adapter.crystallize(
            operation_id=claim_id,
            risk_tier="high",
            facets=facets,
            account_id=account_id,
            policy_id=policy_id,
            reserved_reserve=str(amount) if approved else "0",
        )
        if approved:
            adapter.commit(
                CommitOutcome(
                    operation_id=claim_id,
                    crystal_id=crystal.crystal_id,
                    facets=facets,
                    outcome="paid",
                    committed_reserve=str(amount),
                )
            )
        return crystal.crystal_id
    except Exception:
        return None
