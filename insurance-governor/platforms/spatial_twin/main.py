"""SpatialTwin — LiDAR spatial twin evidence at payout gate."""
from __future__ import annotations

from decimal import Decimal

from fastapi import FastAPI
from pydantic import BaseModel, Field

from platforms.common.platform_sdk import GovernedPlatform, spine_health_payload

from .spatial_gate import evaluate_spatial_damage

app = FastAPI(title="spatialtwin", version="0.1.0")
_GOVERNED = GovernedPlatform("spatial_twin")


class SpatialRequest(BaseModel):
    claim_id: str
    point_count: int
    bounds: dict[str, float] = Field(default_factory=dict)
    damage_estimate: str
    confidence: float = 0.85
    coverage_limit: str = "500000.00"


@app.get("/healthz")
def healthz() -> dict:
    return spine_health_payload("spatial_twin")


@app.get("/readyz")
def readyz() -> dict:
    return healthz()


@app.post("/spatial/evaluate")
def evaluate(request: SpatialRequest) -> dict:
    result = evaluate_spatial_damage(
        claim_id=request.claim_id,
        point_count=request.point_count,
        bounds=request.bounds,
        damage_estimate=Decimal(request.damage_estimate),
        coverage_limit=Decimal(request.coverage_limit),
        confidence=request.confidence,
    )
    facets = {
        "claim_id": request.claim_id,
        "point_cloud_hash": result.point_cloud_hash,
        "damage_estimate": str(result.damage_estimate),
        "spatial_decision": result.decision,
        "confidence": result.confidence,
    }
    crystal_id = _GOVERNED.govern_operation(
        request.claim_id,
        facets,
        decision=result.decision,
        reserve_amount=str(result.damage_estimate) if result.approved else "0",
        outcome="spatial_approved",
    )
    return {
        "decision": result.decision,
        "point_cloud_hash": result.point_cloud_hash,
        "crystal_id": crystal_id,
        "reason": result.reason,
    }
