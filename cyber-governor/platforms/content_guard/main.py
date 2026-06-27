"""ContentGuard — crystal-bound gate before sensitive content publish."""
from __future__ import annotations

import os

from fastapi import FastAPI
from pydantic import BaseModel, Field

from .content_policy import evaluate_content

app = FastAPI(title="content-guard", version="0.1.0")


class ContentEvaluateRequest(BaseModel):
    content_id: str
    principal_id: str
    channel: str = "publish"
    text_body: str
    classification_hint: str = "internal"


class ContentEvaluateResponse(BaseModel):
    content_id: str
    decision: str
    risk_score: float
    matched_patterns: list[str] = Field(default_factory=list)
    redacted_body: str | None = None
    reason: str | None = None
    crystal_id: str | None = None


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok"}


@app.post("/content/evaluate", response_model=ContentEvaluateResponse)
def evaluate(request: ContentEvaluateRequest) -> ContentEvaluateResponse:
    result = evaluate_content(
        text_body=request.text_body,
        channel=request.channel,
        classification_hint=request.classification_hint,
        principal_id=request.principal_id,
    )
    facets = {
        "principal_id": request.principal_id,
        "channel": request.channel,
        "classification_hint": request.classification_hint,
        "content_decision": result.decision,
        "matched_patterns": list(result.matched_patterns),
        "risk_score": result.risk_score,
    }
    if result.redacted_body is not None:
        facets["redacted_body"] = result.redacted_body

    commit_ok = result.decision in {"ALLOWED", "REDACTED"}
    crystal_id = _crystallize_if_spine(request.content_id, facets, approved=commit_ok)
    return ContentEvaluateResponse(
        content_id=request.content_id,
        decision=result.decision,
        risk_score=result.risk_score,
        matched_patterns=list(result.matched_patterns),
        redacted_body=result.redacted_body,
        reason=result.reason,
        crystal_id=crystal_id,
    )


def _crystallize_if_spine(operation_id: str, facets: dict, *, approved: bool) -> str | None:
    if os.environ.get("CG_SPINE_ENABLED", "false").lower() != "true":
        return None
    try:
        from platforms.common.spine_adapter import CommitOutcome, SpineAdapter

        adapter = SpineAdapter(platform="content_guard", spine_enabled=True)
        crystal = adapter.crystallize(
            operation_id=operation_id,
            risk_tier="high",
            facets=facets,
            policy_id="content-high-us",
            account_id="tenant-default",
        )
        if approved:
            adapter.commit(
                CommitOutcome(
                    operation_id=operation_id,
                    crystal_id=crystal.crystal_id,
                    facets=facets,
                    outcome=result_outcome(facets),
                )
            )
        return crystal.crystal_id
    except Exception:
        return None


def result_outcome(facets: dict) -> str:
    if facets.get("content_decision") == "REDACTED":
        return "redacted"
    return "allowed"
