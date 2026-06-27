"""ContentGuard — crystal-bound gate before sensitive content publish."""
from __future__ import annotations

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from platforms.common.platform_sdk import GovernedPlatform, spine_health_payload
from .content_policy import evaluate_content

app = FastAPI(title="content-guard", version="0.1.0")
_GOVERNED = GovernedPlatform("content_guard")


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
    return spine_health_payload("content_guard")


@app.get("/readyz")
def readyz() -> dict:
    return healthz()


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

    crystal_id = None
    if result.decision in {"ALLOWED", "REDACTED"}:
        crystal_id = _GOVERNED.govern_operation(
            request.content_id,
            facets,
            decision=result.decision,
            reserve_amount="0",
            outcome=result.decision.lower(),
        )
    if result.decision == "BLOCKED":
        raise HTTPException(
            status_code=403,
            detail={
                "content_id": request.content_id,
                "decision": result.decision,
                "reason": result.reason,
                "matched_patterns": list(result.matched_patterns),
            },
        )
    return ContentEvaluateResponse(
        content_id=request.content_id,
        decision=result.decision,
        risk_score=result.risk_score,
        matched_patterns=list(result.matched_patterns),
        redacted_body=result.redacted_body,
        reason=result.reason,
        crystal_id=crystal_id,
    )
