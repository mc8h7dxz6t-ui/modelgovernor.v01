"""ClaimGate — governed payout gate with policy engine, SIU, FNOL integrations, payment rail."""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from platforms.common.integrations.fnol_adapter import normalize_fnol
from platforms.common.integrations.fnol_writeback import sync_fnol_decision
from platforms.common.platform_sdk import GovernedPlatform, spine_health_payload

from .payment_rail import PaymentInstruction, submit_payment
from .payout_gate import evaluate_payout, payout_facets
from .policy_rules import DEFAULT_POLICIES, PolicyContext
from .siu_workflow import SiuState

from fastapi import FastAPI

app = FastAPI(title="claimgate", version="0.3.0")
router = APIRouter()
_GOVERNED = GovernedPlatform("claim_gate")


class PayoutRequest(BaseModel):
    claim_id: str
    payout_amount: str
    currency: str = "USD"
    policy_number: str = "POL-AUTO-001"
    loss_date: str | None = None
    siu_flag: bool = False
    fraud_signals: list[str] = Field(default_factory=list)
    account_id: str = "carrier-default"
    policy_id: str = "claim-high-us"
    payee_id: str = "payee-default"
    idempotency_key: str | None = None


class PayoutResponse(BaseModel):
    claim_id: str
    decision: str
    gate_score: float
    net_payable: str
    reason: str | None = None
    crystal_id: str | None = None
    siu_referral_id: str | None = None
    siu_state: str | None = None
    payment_id: str | None = None
    payment_status: str | None = None
    writeback_status: str | None = None
    writeback_external_ref: str | None = None
    rules_applied: list[str] = Field(default_factory=list)


class FnolWebhookRequest(BaseModel):
    vendor: str
    payload: dict[str, Any]


@router.get("/healthz")
def healthz() -> dict:
    return spine_health_payload("claim_gate")


@router.get("/readyz")
def readyz() -> dict:
    return healthz()


@router.get("/policies")
def list_policies() -> dict:
    return {
        k: {
            "coverage_line": v.coverage_line.value,
            "per_occurrence_limit": str(v.per_occurrence_limit),
            "aggregate_limit": str(v.aggregate_limit),
            "deductible": str(v.deductible),
            "auto_approve_limit": str(v.auto_approve_limit),
        }
        for k, v in DEFAULT_POLICIES.items()
    }


def _resolve_policy(policy_number: str) -> PolicyContext:
    if policy_number not in DEFAULT_POLICIES:
        raise HTTPException(status_code=404, detail=f"unknown policy: {policy_number}")
    return DEFAULT_POLICIES[policy_number]


def _run_evaluation(request: PayoutRequest) -> PayoutResponse:
    amount = Decimal(request.payout_amount)
    policy = _resolve_policy(request.policy_number)
    loss = date.fromisoformat(request.loss_date) if request.loss_date else date.today()

    result = evaluate_payout(
        claim_id=request.claim_id,
        payout_amount=amount,
        policy=policy,
        loss_date=loss,
        siu_flag=request.siu_flag,
        fraud_signals=request.fraud_signals,
    )

    siu_id = result.siu_referral.referral_id if result.siu_referral else None
    siu_state = result.siu_referral.state.value if result.siu_referral else None
    rules = result.policy_trace.rules_applied if result.policy_trace else []

    facets = payout_facets(
        claim_id=request.claim_id,
        payout_amount=amount,
        currency=request.currency,
        decision=result.decision,
        score=result.score,
        net_payable=result.net_payable,
        policy_number=request.policy_number,
        siu_referral_id=siu_id,
    )

    crystal_id = _GOVERNED.govern_operation(
        request.claim_id,
        facets,
        decision=result.decision,
        reserve_amount=str(result.net_payable),
        account_id=request.account_id,
        policy_id=request.policy_id,
        outcome="paid",
    )

    payment: PaymentInstruction | None = None
    if request.idempotency_key:
        payment = submit_payment(
            claim_id=request.claim_id,
            amount=result.net_payable,
            currency=request.currency,
            payee_id=request.payee_id,
            idempotency_key=request.idempotency_key,
            gate_decision=result.decision,
            crystal_id=crystal_id,
        )
        if payment.payment_id:
            facets["payment_id"] = payment.payment_id

    return PayoutResponse(
        claim_id=request.claim_id,
        decision=result.decision,
        gate_score=result.score,
        net_payable=str(result.net_payable),
        reason=result.reason,
        crystal_id=crystal_id,
        siu_referral_id=siu_id,
        siu_state=siu_state,
        payment_id=payment.payment_id if payment else None,
        payment_status=payment.status.value if payment else None,
        rules_applied=rules,
    )


@router.post("/claim/evaluate", response_model=PayoutResponse)
def evaluate(request: PayoutRequest) -> PayoutResponse:
    return _run_evaluation(request)


@router.post("/claim/fnol/webhook", response_model=PayoutResponse)
def fnol_webhook(body: FnolWebhookRequest) -> PayoutResponse:
    try:
        fnol = normalize_fnol(body.vendor, body.payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    req = PayoutRequest(
        claim_id=fnol.claim_id,
        payout_amount=str(fnol.reported_amount),
        currency=fnol.currency,
        policy_number=fnol.policy_number,
        loss_date=fnol.loss_date.isoformat(),
        fraud_signals=fnol.fraud_signals,
        idempotency_key=f"fnol-{fnol.vendor}-{fnol.raw_vendor_id}",
        payee_id=fnol.claimant_id,
    )
    response = _run_evaluation(req)
    writeback = sync_fnol_decision(
        vendor=fnol.vendor,
        claim_id=fnol.claim_id,
        decision=response.decision,
        facets={
            "gate_score": response.gate_score,
            "net_payable": response.net_payable,
            "crystal_id": response.crystal_id,
            "payment_id": response.payment_id,
        },
    )
    return response.model_copy(
        update={
            "reason": response.reason or f"fnol_{fnol.vendor}",
            "writeback_status": writeback.status,
            "writeback_external_ref": writeback.external_ref,
        }
    )


@router.post("/claim/siu/refer")
def siu_refer(claim_id: str, signals: list[str]) -> dict:
    from .siu_workflow import evaluate_siu

    referral = evaluate_siu(claim_id=claim_id, signals=signals, siu_flag=True)
    return {
        "referral_id": referral.referral_id,
        "state": referral.state.value,
        "fraud_score": referral.fraud_score,
        "signals": referral.signals,
    }


app.include_router(router)
