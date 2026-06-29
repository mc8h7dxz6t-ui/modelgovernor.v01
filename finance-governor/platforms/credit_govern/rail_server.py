"""Reference HTTP inference rail for production integration testing."""
from __future__ import annotations

from decimal import Decimal

from fastapi import FastAPI
from pydantic import BaseModel, Field

app = FastAPI(title="fg-credit-rail-reference", version="0.1.0")


class ScoreRequest(BaseModel):
    application_id: str
    exposure_amount: str
    model_version_id: str
    features: dict = Field(default_factory=dict)


class ScoreResponse(BaseModel):
    decision: str
    score: float
    explanation_id: str


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok"}


@app.post("/v1/score", response_model=ScoreResponse)
def score(request: ScoreRequest) -> ScoreResponse:
    exposure = Decimal(request.exposure_amount)
    if request.model_version_id.startswith("unapproved"):
        return ScoreResponse(decision="BLOCKED", score=0.0, explanation_id="exp-rail-model-block")
    if exposure > Decimal("250000"):
        return ScoreResponse(decision="REFER", score=0.55, explanation_id="exp-rail-high-exposure")
    return ScoreResponse(decision="APPROVE", score=0.84, explanation_id="exp-rail-auto-approve")
