"""WireMatch gate API — semantic pre-send gate vs payment hub schema-only checks."""
from __future__ import annotations

import os
from decimal import Decimal

from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel

from platforms.common.platform_metrics import get_platform_metrics

from .execution_gate import evaluate_and_gate, get_wire_event_store, send_wire
from .iso20022_adapter import parse_pacs008_stub
from .semantic_matcher import GoldenRecord
from .wire_schema import WireRequest

app = FastAPI(title="wirematch", version="0.2.0")

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


class Iso20022Request(BaseModel):
    message: str
    idempotency_key: str | None = None


class SendRequest(BaseModel):
    wire_id: str
    beneficiary_name: str
    beneficiary_account: str
    amount: str
    currency: str = "USD"
    idempotency_key: str | None = None


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok"}


@app.get("/readyz")
def readyz() -> dict:
    return {"ready": True}


@app.get("/metrics")
def metrics() -> Response:
    return Response(content=get_platform_metrics().prometheus_text(), media_type="text/plain")


@app.post("/wire/evaluate", response_model=EvaluateResponse)
def evaluate(wire: WireRequest) -> EvaluateResponse:
    amount = Decimal(wire.amount)
    decision = evaluate_and_gate(
        wire_id=wire.wire_id,
        beneficiary_name=wire.beneficiary_name,
        beneficiary_account=wire.beneficiary_account,
        amount=amount,
        golden=_GOLDEN,
    )
    facets = {
        "amount": wire.amount,
        "currency": wire.currency,
        "beneficiary_hash": wire.beneficiary_account,
        "semantic_score": decision.match_score,
    }
    crystal_id = _crystallize_if_spine(wire.wire_id, facets, approved=decision.decision == "APPROVED")

    return EvaluateResponse(
        wire_id=wire.wire_id,
        decision=decision.decision,
        match_score=decision.match_score,
        reason=decision.reason,
        crystal_id=crystal_id,
    )


@app.post("/wire/evaluate-iso20022", response_model=EvaluateResponse)
def evaluate_iso20022(body: Iso20022Request) -> EvaluateResponse:
    try:
        intent = parse_pacs008_stub(body.message)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    decision = evaluate_and_gate(
        wire_id=intent.wire_id,
        beneficiary_name=intent.beneficiary_name,
        beneficiary_account=intent.beneficiary_account,
        amount=intent.amount,
        golden=_GOLDEN,
        idempotency_key=body.idempotency_key,
    )
    return EvaluateResponse(
        wire_id=intent.wire_id,
        decision=decision.decision,
        match_score=decision.match_score,
        reason=decision.reason,
    )


@app.post("/wire/send")
def wire_send(body: SendRequest) -> dict:
    amount = Decimal(body.amount)
    decision = evaluate_and_gate(
        wire_id=body.wire_id,
        beneficiary_name=body.beneficiary_name,
        beneficiary_account=body.beneficiary_account,
        amount=amount,
        golden=_GOLDEN,
        idempotency_key=body.idempotency_key,
    )
    result = send_wire(decision, amount=amount)
    if result["status"] == "SENT":
        _crystallize_if_spine(
            body.wire_id,
            {"amount": body.amount, "semantic_score": decision.match_score},
            approved=True,
        )
    return result


@app.get("/internal/events/recent")
def recent_events(limit: int = 20) -> dict:
    events = get_wire_event_store().recent(limit)
    return {
        "events": [
            {
                "seq": e.seq,
                "event_type": e.event_type,
                "operation_id": e.operation_id,
                "payload": e.payload,
            }
            for e in events
        ],
        "chain_valid": get_wire_event_store().verify_chain(),
    }


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
