"""UnderwritingGovern — D&O / regulatory liability loss control for AI underwriting."""
from __future__ import annotations

from decimal import Decimal

from fastapi import FastAPI
from pydantic import BaseModel, Field

from platforms.common.platform_sdk import GovernedPlatform, spine_health_payload

from .fairness_gate import evaluate_underwriting_fairness

app = FastAPI(title="underwritinggovern", version="0.1.0")
_GOVERNED = GovernedPlatform("underwriting_govern")


class UnderwriteRequest(BaseModel):
    application_id: str
    model_score: float
    requested_limit: str = "0"
    jurisdiction: str = "US"
    protected_attribute_deltas: dict[str, float] = Field(default_factory=dict)
    product_line: str = "commercial_auto"


@app.get("/healthz")
def healthz() -> dict:
    return spine_health_payload("underwriting_govern")


@app.post("/underwrite/evaluate")
def evaluate(request: UnderwriteRequest) -> dict:
    limit = Decimal(request.requested_limit)
    auto_limit = Decimal("750000") if request.jurisdiction.upper() in ("UK", "GB") else Decimal("500000")
    result = evaluate_underwriting_fairness(
        application_id=request.application_id,
        score=request.model_score,
        protected_attribute_deltas=request.protected_attribute_deltas,
        jurisdiction=request.jurisdiction,
        auto_approve_limit=auto_limit,
        requested_limit=limit,
    )
    facets = {
        "application_id": request.application_id,
        "govern_decision": result.decision,
        "bias_score": result.bias_score,
        "jurisdiction": request.jurisdiction.upper(),
        "product_line": request.product_line,
        "adverse_action_required": result.adverse_action_required,
    }
    crystal_id = _GOVERNED.govern_operation(
        request.application_id,
        facets,
        decision=result.decision,
        reserve_amount=request.requested_limit if result.compliant else "0",
        outcome="underwritten",
    )
    return {
        "application_id": request.application_id,
        "decision": result.decision,
        "bias_score": result.bias_score,
        "reason": result.reason,
        "adverse_action_required": result.adverse_action_required,
        "crystal_id": crystal_id,
        "regulatory_refs": _regulatory_refs(request.jurisdiction),
    }


def _regulatory_refs(jurisdiction: str) -> list[str]:
    if jurisdiction.upper() in ("UK", "GB"):
        return ["FCA Consumer Duty", "PRA SS1/23", "Equality Act 2010"]
    return ["ECOA", "FCRA", "NAIC Model Audit Rule", "state DOI unfair discrimination"]
