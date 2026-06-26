"""EgressLock — crystal-bound gate before data exfiltration."""
from __future__ import annotations

import os

from fastapi import FastAPI
from pydantic import BaseModel, Field

from .egress_policy import EgressPolicy, evaluate_egress

app = FastAPI(title="egress-lock", version="0.1.0")

_POLICY = EgressPolicy(
    max_bytes_without_review=50_000_000,
    blocked_destinations=frozenset({"evil-exfil.example", "pastebin.com"}),
)


class EgressRequest(BaseModel):
    egress_id: str
    principal_id: str
    destination: str
    byte_count: int = Field(ge=0)
    resource_type: str = "object"
    protocol: str = "https"


class EgressResponse(BaseModel):
    egress_id: str
    decision: str
    risk_score: float
    reason: str | None = None
    crystal_id: str | None = None


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok"}


@app.post("/egress/evaluate", response_model=EgressResponse)
def evaluate(request: EgressRequest) -> EgressResponse:
    result = evaluate_egress(
        destination=request.destination,
        byte_count=request.byte_count,
        principal_id=request.principal_id,
        policy=_POLICY,
    )
    facets = {
        "principal_id": request.principal_id,
        "destination": request.destination,
        "byte_count": request.byte_count,
        "resource_type": request.resource_type,
        "protocol": request.protocol,
        "risk_score": result.risk_score,
    }
    crystal_id = _crystallize_if_spine(request.egress_id, facets, approved=result.approved)
    return EgressResponse(
        egress_id=request.egress_id,
        decision="ALLOWED" if result.approved else "BLOCKED",
        risk_score=result.risk_score,
        reason=result.reason,
        crystal_id=crystal_id,
    )


def _crystallize_if_spine(operation_id: str, facets: dict, *, approved: bool) -> str | None:
    if os.environ.get("CG_SPINE_ENABLED", "false").lower() != "true":
        return None
    try:
        from platforms.common.spine_adapter import CommitOutcome, SpineAdapter

        adapter = SpineAdapter(platform="egress_lock", spine_enabled=True)
        crystal = adapter.crystallize(
            operation_id=operation_id,
            risk_tier="critical",
            facets=facets,
            policy_id="egress-critical-us",
            account_id="tenant-default",
            reserved_exposure=str(facets.get("byte_count", "0")),
        )
        if approved:
            adapter.commit(
                CommitOutcome(
                    operation_id=operation_id,
                    crystal_id=crystal.crystal_id,
                    facets=facets,
                    outcome="allowed",
                    committed_exposure=str(facets.get("byte_count", "0")),
                )
            )
        return crystal.crystal_id
    except Exception:
        return None
