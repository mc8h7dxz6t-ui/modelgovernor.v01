"""CreditGovern gate API."""
from __future__ import annotations

import logging
import os
from decimal import Decimal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from platforms.common.platform_metrics import get_platform_counters
from platforms.common.platform_observability import mount_platform_observability
from platforms.common.platform_store import append_platform_event, get_credit_store, reset_all_stores

from .credit_schema import CreditRequest
from .inference_rail import RailCircuitOpenError, get_inference_rail, reset_inference_rail

logger = logging.getLogger(__name__)

app = FastAPI(title="credit-govern", version="0.2.0")
_store = get_credit_store()
_COUNTERS = get_platform_counters("credit_govern")

_APPROVED_MODELS = {"credit-model-v3", "credit-model-v4"}

mount_platform_observability(app, platform="credit_govern", ready_check=lambda: _store.ready())


class EvaluateResponse(BaseModel):
    application_id: str
    decision: str
    score: float
    explanation_id: str
    crystal_id: str | None = None
    reason: str | None = None


@app.post("/credit/evaluate", response_model=EvaluateResponse)
def evaluate(req: CreditRequest) -> EvaluateResponse:
    exposure = Decimal(req.exposure_amount)

    if req.model_version_id not in _APPROVED_MODELS:
        _COUNTERS.increment("model_version_blocked_total")
        append_platform_event(
            "credit_govern",
            "MODEL_VERSION_BLOCKED",
            req.application_id,
            {"model_version_id": req.model_version_id},
        )
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
            _record_rail_attempt(req.application_id, "RESERVED", crystal_id)
        except Exception as exc:
            logger.warning("exposure reserve failed: %s", exc)
            _COUNTERS.increment("rail_circuit_open_total")
            raise HTTPException(status_code=409, detail="INSUFFICIENT_EXPOSURE") from exc

    outcome = _score_with_rail(req, exposure)
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
            if facets.get("desk_id") != req.desk_id:
                _COUNTERS.increment("attribution_identity_mismatch_total")
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
            _record_rail_attempt(req.application_id, outcome.decision, outcome.explanation_id)
        except Exception as exc:
            logger.warning("commit failed: %s", exc)

    _store.record_evaluation(
        {
            "application_id": req.application_id,
            "decision": outcome.decision,
            "exposure_amount": req.exposure_amount,
            "model_version_id": req.model_version_id,
            "desk_id": req.desk_id,
            "score": outcome.score,
            "explanation_id": outcome.explanation_id,
            "crystal_id": crystal_id,
        }
    )

    return EvaluateResponse(
        application_id=req.application_id,
        decision=outcome.decision,
        score=outcome.score,
        explanation_id=outcome.explanation_id,
        crystal_id=crystal_id,
        reason=None if outcome.decision != "BLOCKED" else "RAIL_BLOCKED",
    )


def _score_with_rail(req: CreditRequest, exposure: Decimal):
    _COUNTERS.increment("rail_attempt_total")
    rail = get_inference_rail()
    try:
        return rail.score(
            application_id=req.application_id,
            exposure=exposure,
            model_version_id=req.model_version_id,
            features={
                "desk_id": req.desk_id,
                "feature_snapshot_hash": req.feature_snapshot_hash,
            },
        )
    except RailCircuitOpenError as exc:
        _COUNTERS.increment("rail_circuit_open_total")
        raise HTTPException(status_code=503, detail="RAIL_CIRCUIT_OPEN") from exc


def _record_rail_attempt(application_id: str, status: str, external_ref: str | None) -> None:
    if os.environ.get("FG_SPINE_ENABLED", "false").lower() != "true":
        return
    try:
        import httpx

        sidecar = os.environ.get("FG_SIDECAR_URL", "http://localhost:8091").rstrip("/")
        token = os.environ.get("FG_INTERNAL_TOKEN", "dev-fg-spine-token-change-me")
        with httpx.Client(timeout=5.0) as client:
            client.post(
                f"{sidecar}/internal/rail/attempt",
                headers={"x-internal-token": token, "content-type": "application/json"},
                json={
                    "operation_id": application_id,
                    "platform": "credit_govern",
                    "attempt_status": status,
                    "external_ref": external_ref,
                },
            )
    except Exception as exc:
        logger.debug("rail attempt record skipped: %s", exc)


def reset_state() -> None:
    reset_all_stores()
    reset_inference_rail()
