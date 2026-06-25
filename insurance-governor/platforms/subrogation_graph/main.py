"""SubrogationGraph — GNN-informed subrogation recovery routing."""
from __future__ import annotations

from decimal import Decimal

from fastapi import FastAPI
from pydantic import BaseModel, Field

from platforms.common.platform_sdk import GovernedPlatform, spine_health_payload

from .graph_gate import evaluate_subrogation_graph

app = FastAPI(title="subrogationgraph", version="0.1.0")
_GOVERNED = GovernedPlatform("subrogation_graph")


class GraphRequest(BaseModel):
    claim_id: str
    total_loss: str
    defendants: dict[str, float] = Field(default_factory=dict)


@app.get("/healthz")
def healthz() -> dict:
    return spine_health_payload("subrogation_graph")


@app.post("/subrogation/evaluate")
def evaluate(request: GraphRequest) -> dict:
    result = evaluate_subrogation_graph(
        claim_id=request.claim_id,
        total_loss=Decimal(request.total_loss),
        defendants=request.defendants,
    )
    facets = {
        "claim_id": request.claim_id,
        "primary_defendant": result.primary_defendant,
        "graph_score": result.graph_score,
        "subrogation_decision": result.decision,
        "recovery_amount": str(result.recovery_amount),
    }
    crystal_id = _GOVERNED.govern_operation(
        request.claim_id,
        facets,
        decision=result.decision,
        reserve_amount=str(result.recovery_amount) if result.recoverable else "0",
        outcome="recovery",
    )
    return {
        "decision": result.decision,
        "recovery_amount": str(result.recovery_amount),
        "primary_defendant": result.primary_defendant,
        "crystal_id": crystal_id,
    }
