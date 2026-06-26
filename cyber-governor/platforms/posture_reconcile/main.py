"""PostureReconcile — crystal-bound posture gate before authorize/deploy."""
from __future__ import annotations

import os

from fastapi import FastAPI
from pydantic import BaseModel, Field

from .posture_policy import PostureBaseline, evaluate_posture

app = FastAPI(title="posture-reconcile", version="0.1.0")

_DEMO_BASELINE = PostureBaseline(
    baseline_id="baseline-corp-prod-v3",
    min_posture_score=80,
    critical_controls=frozenset(
        {"public_s3_bucket", "admin_port_open", "unencrypted_volume"},
    ),
)


class PostureEvaluateRequest(BaseModel):
    evaluation_id: str
    resource_id: str
    source: str = "generic"
    posture_score: int = Field(ge=0, le=100)
    failed_controls: list[str] = Field(default_factory=list)
    approved_baseline_id: str = "baseline-corp-prod-v3"


class PostureEvaluateResponse(BaseModel):
    evaluation_id: str
    decision: str
    posture_state: str
    drift_score: float
    reason: str | None = None
    crystal_id: str | None = None


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok"}


@app.post("/posture/evaluate", response_model=PostureEvaluateResponse)
def evaluate(request: PostureEvaluateRequest) -> PostureEvaluateResponse:
    result = evaluate_posture(
        posture_score=request.posture_score,
        failed_controls=request.failed_controls,
        baseline=_DEMO_BASELINE,
    )
    facets = {
        "resource_id": request.resource_id,
        "source": request.source,
        "posture_score": request.posture_score,
        "failed_controls": request.failed_controls,
        "approved_baseline_id": request.approved_baseline_id,
        "posture_state": result.posture_state,
        "drift_score": result.drift_score,
        "decision": result.decision,
    }
    crystal_id = _crystallize_if_spine(request.evaluation_id, facets, approved=result.approved)
    return PostureEvaluateResponse(
        evaluation_id=request.evaluation_id,
        decision=result.decision,
        posture_state=result.posture_state,
        drift_score=result.drift_score,
        reason=result.reason,
        crystal_id=crystal_id,
    )


def _crystallize_if_spine(operation_id: str, facets: dict, *, approved: bool) -> str | None:
    if os.environ.get("CG_SPINE_ENABLED", "false").lower() != "true":
        return None
    try:
        from platforms.common.spine_adapter import CommitOutcome, SpineAdapter

        adapter = SpineAdapter(platform="posture_reconcile", spine_enabled=True)
        crystal = adapter.crystallize(
            operation_id=operation_id,
            risk_tier="high",
            facets=facets,
            policy_id="posture-high-us",
            account_id="tenant-default",
        )
        if approved:
            adapter.commit(
                CommitOutcome(
                    operation_id=operation_id,
                    crystal_id=crystal.crystal_id,
                    facets=facets,
                    outcome="allowed",
                )
            )
        return crystal.crystal_id
    except Exception:
        return None
