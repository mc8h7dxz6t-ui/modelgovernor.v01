"""ReserveReconcile — reinsurance / intercompany reserve sync (operational risk loss control)."""
from __future__ import annotations

from decimal import Decimal

from fastapi import FastAPI
from pydantic import BaseModel

from platforms.common.platform_sdk import GovernedPlatform, spine_health_payload

from .reconcile_gate import evaluate_reserve_match

app = FastAPI(title="reservereconcile", version="0.1.0")
_GOVERNED = GovernedPlatform("reserve_reconcile")


class ReserveMatchRequest(BaseModel):
    claim_id: str
    case_reserve: str
    reinsurance_reserve: str
    ic_ledger_reserve: str | None = None
    jurisdiction: str = "US"
    currency: str = "USD"


@app.get("/healthz")
def healthz() -> dict:
    return spine_health_payload("reserve_reconcile")


@app.post("/reserve/match")
def match(request: ReserveMatchRequest) -> dict:
    case = Decimal(request.case_reserve)
    reins = Decimal(request.reinsurance_reserve)
    ic = Decimal(request.ic_ledger_reserve) if request.ic_ledger_reserve else None
    tolerance = Decimal("0.01") if request.jurisdiction.upper() in ("UK", "GB") else Decimal("0.02")
    result = evaluate_reserve_match(
        claim_id=request.claim_id,
        case_reserve=case,
        reinsurance_reserve=reins,
        ic_ledger_reserve=ic,
        tolerance_pct=tolerance,
        jurisdiction=request.jurisdiction,
    )
    facets = {
        "claim_id": request.claim_id,
        "match_state": result.match_state,
        "drift_amount": str(result.drift_amount),
        "jurisdiction": request.jurisdiction.upper(),
        "currency": request.currency,
    }
    crystal_id = _GOVERNED.govern_operation(
        request.claim_id,
        facets,
        decision=result.decision,
        reserve_amount=str(case) if result.matched else "0",
        outcome="reconciled",
    )
    return {
        "claim_id": request.claim_id,
        "decision": result.decision,
        "match_state": result.match_state,
        "drift_amount": str(result.drift_amount),
        "reason": result.reason,
        "crystal_id": crystal_id,
    }
