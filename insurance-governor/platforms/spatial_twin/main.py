"""SpatialTwin — governed spatial evidence envelope at payout gate (production LiDAR vendor = SOW)."""
from __future__ import annotations

from decimal import Decimal

from fastapi import FastAPI, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field

from platforms.common.platform_metrics import render_prometheus_text
from platforms.common.platform_sdk import GovernedPlatform, increment_invariant, spine_health_payload

from .spatial_gate import evaluate_spatial_damage
from .spatial_ingest import fetch_spatial_vendor_feed, verify_spatial_attestation

app = FastAPI(title="spatialtwin", version="0.2.0")
_GOVERNED = GovernedPlatform("spatial_twin")


class SpatialRequest(BaseModel):
    claim_id: str
    point_count: int
    bounds: dict[str, float] = Field(default_factory=dict)
    damage_estimate: str
    confidence: float = 0.85
    coverage_limit: str = "500000.00"
    deductible: str = "0"
    scan_age_days: int = 0
    vendor: str = "matterport-mock"
    vendor_payload: str | None = None
    vendor_attestation_hash: str | None = None


@app.get("/healthz")
def healthz() -> dict:
    return spine_health_payload("spatial_twin")


@app.get("/readyz")
def readyz() -> dict:
    return healthz()


@app.get("/metrics", response_class=PlainTextResponse)
def metrics() -> str:
    return render_prometheus_text("spatial_twin")


@app.get("/spatial/feed")
def feed(vendor: str | None = None) -> dict:
    reading = fetch_spatial_vendor_feed(vendor=vendor)
    return {
        "vendor": reading.vendor,
        "claim_id": reading.claim_id,
        "point_count": reading.point_count,
        "bounds": reading.bounds,
        "damage_estimate": str(reading.damage_estimate),
        "confidence": reading.confidence,
        "scan_age_days": reading.scan_age_days,
        "vendor_payload": reading.payload,
        "vendor_attestation_hash": reading.attestation_hash,
    }


@app.post("/spatial/evaluate")
def evaluate(request: SpatialRequest) -> dict:
    if request.vendor_payload and request.vendor_attestation_hash:
        if not verify_spatial_attestation(
            vendor=request.vendor,
            payload=request.vendor_payload,
            attestation_hash_value=request.vendor_attestation_hash,
        ):
            increment_invariant("spatial_twin", "spatial_attestation_mismatch_total")
            raise HTTPException(status_code=422, detail="vendor attestation mismatch")

    result = evaluate_spatial_damage(
        claim_id=request.claim_id,
        point_count=request.point_count,
        bounds=request.bounds,
        damage_estimate=Decimal(request.damage_estimate),
        coverage_limit=Decimal(request.coverage_limit),
        confidence=request.confidence,
        deductible=Decimal(request.deductible),
        scan_age_days=request.scan_age_days,
    )

    if result.decision == "APPROVED":
        increment_invariant("spatial_twin", "spatial_approved_total")
    elif result.decision == "HELD":
        increment_invariant("spatial_twin", "spatial_held_total")
    elif result.decision == "REFERRED":
        increment_invariant("spatial_twin", "spatial_referred_total")
    else:
        increment_invariant("spatial_twin", "spatial_declined_total")

    facets = {
        "claim_id": request.claim_id,
        "point_cloud_hash": result.point_cloud_hash,
        "damage_estimate": str(result.damage_estimate),
        "net_damage": str(result.net_damage),
        "spatial_decision": result.decision,
        "confidence": result.confidence,
        "vendor": request.vendor,
    }
    crystal_id = _GOVERNED.govern_operation(
        request.claim_id,
        facets,
        decision=result.decision,
        reserve_amount=str(result.net_damage) if result.approved else "0",
        outcome="spatial_approved",
    )
    return {
        "decision": result.decision,
        "point_cloud_hash": result.point_cloud_hash,
        "net_damage": str(result.net_damage),
        "crystal_id": crystal_id,
        "reason": result.reason,
    }
