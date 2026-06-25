"""CreditGovern gate API."""
from __future__ import annotations

import logging
import os
from decimal import Decimal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from .credit_schema import CreditRequest
from .mock_rail import score_application

logger = logging.getLogger(__name__)

app = FastAPI(title="credit-govern", version="0.1.0")

_APPROVED_MODELS = {"credit-model-v3", "credit-model-v4"}


class EvaluateResponse(BaseModel):
    application_id: str
    decision: str
    score: float
    explanation_id: str
    crystal_id: str | None = None
    reason: str | None = None


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok"}


@app.post("/credit/evaluate", response_model=EvaluateResponse)
def evaluate(req: CreditRequest) -> EvaluateResponse:
    exposure = Decimal(req.exposure_amount)

    if req.model_version_id not in _APPROVED_MODELS:
        return EvaluateResponse(
            application_id=req.application_id,
            decision="BLOCKED",
            score=0.0,
            explanation_id="",
            reason="MODEL_VERSION_MISMATCH",
        )

    spine_on = os.environ.get("FG_SPINE_ENABLED", "false").lower() == "true"
    adapter = None
    crystal_id: str | None = None

    if spine_on:
        try:
            from platforms.common.spine_adapter import SpineAdapter

            adapter = SpineAdapter(platform="credit_govern", spine_enabled=True)
            crystal = adapter.crystallize(
                operation_id=req.application_id,
                risk_tier="high",
                facets={
                    "application_id": req.application_id,
                    "exposure_amount": req.exposure_amount,
                    "model_version_id": req.model_version_id,
                    "desk_id": req.desk_id,
                },
                account_id=req.desk_id,
                policy_id="credit-high-us",
                reserved_exposure=str(exposure),
            )
            crystal_id = crystal.crystal_id
        except Exception as exc:
            logger.warning("exposure reserve failed: %s", exc)
            raise HTTPException(status_code=409, detail="INSUFFICIENT_EXPOSURE") from exc

    outcome = score_application(exposure=exposure, model_version_id=req.model_version_id)
    facets = {
        "application_id": req.application_id,
        "exposure_amount": req.exposure_amount,
        "model_version_id": req.model_version_id,
        "desk_id": req.desk_id,
        "feature_snapshot_hash": req.feature_snapshot_hash,
        "score": outcome.score,
        "explanation_id": outcome.explanation_id,
    }

    if adapter and crystal_id:
        try:
            from platforms.common.spine_adapter import CommitOutcome

            committed = str(exposure) if outcome.decision == "APPROVE" else "0"
            adapter.commit(
                CommitOutcome(
                    operation_id=req.application_id,
                    crystal_id=crystal_id,
                    facets=facets,
                    outcome=outcome.decision.lower(),
                    committed_exposure=committed,
                    metadata={"explanation_id": outcome.explanation_id},
                )
            )
        except Exception as exc:
            logger.warning("commit failed: %s", exc)

    return EvaluateResponse(
        application_id=req.application_id,
        decision=outcome.decision,
        score=outcome.score,
        explanation_id=outcome.explanation_id,
        crystal_id=crystal_id,
        reason=None if outcome.decision != "BLOCKED" else "RAIL_BLOCKED",
    )
