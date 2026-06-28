"""SubrogationGraph — governed subrogation desk evidence envelope (live desk API = SOW)."""
from __future__ import annotations

from decimal import Decimal

from fastapi import FastAPI, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field

from platforms.common.platform_metrics import render_prometheus_text
from platforms.common.platform_sdk import GovernedPlatform, increment_invariant, spine_health_payload

from .desk_ingest import fetch_subro_desk_feed, verify_subro_attestation
from .graph_gate import evaluate_subrogation_graph

app = FastAPI(title="subrogationgraph", version="0.2.0")
_GOVERNED = GovernedPlatform("subrogation_graph")


class GraphRequest(BaseModel):
    claim_id: str
    total_loss: str
    defendants: dict[str, float] = Field(default_factory=dict)
    salvage_offset: str = "0"
    statute_expired: bool = False
    vendor: str = "subro-desk-mock"
    vendor_payload: str | None = None
    vendor_attestation_hash: str | None = None


@app.get("/healthz")
def healthz() -> dict:
    return spine_health_payload("subrogation_graph")


@app.get("/readyz")
def readyz() -> dict:
    return healthz()


@app.get("/metrics", response_class=PlainTextResponse)
def metrics() -> str:
    return render_prometheus_text("subrogation_graph")


@app.get("/subrogation/feed")
def feed(vendor: str | None = None) -> dict:
    reading = fetch_subro_desk_feed(vendor=vendor)
    return {
        "vendor": reading.vendor,
        "claim_id": reading.claim_id,
        "total_loss": str(reading.total_loss),
        "defendants": reading.defendants,
        "salvage_offset": str(reading.salvage_offset),
        "statute_expired": reading.statute_expired,
        "vendor_payload": reading.payload,
        "vendor_attestation_hash": reading.attestation_hash,
    }


@app.post("/subrogation/evaluate")
def evaluate(request: GraphRequest) -> dict:
    if request.vendor_payload and request.vendor_attestation_hash:
        if not verify_subro_attestation(
            vendor=request.vendor,
            payload=request.vendor_payload,
            attestation_hash_value=request.vendor_attestation_hash,
        ):
            increment_invariant("subrogation_graph", "subro_attestation_mismatch_total")
            raise HTTPException(status_code=422, detail="vendor attestation mismatch")

    result = evaluate_subrogation_graph(
        claim_id=request.claim_id,
        total_loss=Decimal(request.total_loss),
        defendants=request.defendants,
        salvage_offset=Decimal(request.salvage_offset),
        statute_expired=request.statute_expired,
    )

    if result.decision == "RECOVERY_APPROVED":
        increment_invariant("subrogation_graph", "subro_recovery_approved_total")
    elif result.decision == "NO_RECOVERY":
        increment_invariant("subrogation_graph", "subro_no_recovery_total")
    else:
        increment_invariant("subrogation_graph", "subro_referred_total")

    facets = {
        "claim_id": request.claim_id,
        "primary_defendant": result.primary_defendant,
        "graph_score": result.graph_score,
        "subrogation_decision": result.decision,
        "recovery_amount": str(result.recovery_amount),
        "vendor": request.vendor,
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
        "reason": result.reason,
    }
