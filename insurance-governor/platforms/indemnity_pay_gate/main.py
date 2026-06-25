"""IndemnityPayGate — Crime / FI bond indemnity payment loss control."""
from __future__ import annotations

from decimal import Decimal

from fastapi import FastAPI
from pydantic import BaseModel

from platforms.common.platform_sdk import GovernedPlatform, spine_health_payload

from .pay_gate import GOLDEN_BY_JURISDICTION, evaluate_indemnity_payment

app = FastAPI(title="indemnitypaygate", version="0.1.0")
_GOVERNED = GovernedPlatform("indemnity_pay_gate")


class IndemnityRequest(BaseModel):
    payment_id: str
    payee_name: str
    payee_account: str
    amount: str
    currency: str = "USD"
    jurisdiction: str = "US"
    social_engineering_flag: bool = False
    claim_id: str | None = None


@app.get("/healthz")
def healthz() -> dict:
    return spine_health_payload("indemnity_pay_gate")


@app.get("/readyz")
def readyz() -> dict:
    return healthz()


@app.post("/indemnity/evaluate")
def evaluate(request: IndemnityRequest) -> dict:
    golden = GOLDEN_BY_JURISDICTION.get(request.jurisdiction.upper(), GOLDEN_BY_JURISDICTION["US"])
    amount = Decimal(request.amount)
    result = evaluate_indemnity_payment(
        payment_id=request.payment_id,
        payee_name=request.payee_name,
        payee_account=request.payee_account,
        amount=amount,
        golden=golden,
        social_engineering_flag=request.social_engineering_flag,
    )
    facets = {
        "payment_id": request.payment_id,
        "payee_hash": request.payee_account,
        "semantic_score": result.score,
        "indemnity_decision": result.decision,
        "jurisdiction": request.jurisdiction.upper(),
        "currency": request.currency,
    }
    if request.claim_id:
        facets["claim_id"] = request.claim_id
    crystal_id = _GOVERNED.govern_operation(
        request.payment_id,
        facets,
        decision=result.decision,
        reserve_amount=request.amount if result.approved else "0",
        outcome="indemnity_paid",
    )
    return {
        "payment_id": request.payment_id,
        "decision": result.decision,
        "match_score": result.score,
        "reason": result.reason,
        "crystal_id": crystal_id,
        "warranty_note": "mesh blocks payout when model_risk_freeze=FROZEN or claim_gate=REFERRED",
    }
