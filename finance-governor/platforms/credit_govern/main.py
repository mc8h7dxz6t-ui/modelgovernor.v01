"""CreditGovern gate API."""
from __future__ import annotations

import logging
import os
from decimal import Decimal

from fastapi import FastAPI, HTTPException, HTTPException
from pydantic import BaseModel

from platforms.common.bias_monitoring import record_credit_cohort
from platforms.common.platform_configs import CREDIT_GOVERN_CONFIG
from platforms.common.platform_sdk import create_platform_app, increment_invariant, spine_enabled
from platforms.common.platform_store import append_platform_event, get_credit_store, reset_all_stores
from platforms.common.spine_helpers import adapter_for

from .credit_schema import CreditRequest
from .inference_rail import RailCircuitOpenError, get_inference_rail, reset_inference_rail

logger = logging.getLogger(__name__)

CONFIG = CREDIT_GOVERN_CONFIG
_store = get_credit_store()
_APPROVED_MODELS = {"credit-model-v3", "credit-model-v4"}

app = create_platform_app(CONFIG, ready_check=lambda: _store.ready())


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
        increment_invariant(CONFIG.name, "model_version_blocked_total")
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

    facets = {
        "application_id": req.application_id,
        "exposure_amount": req.exposure_amount,
        "model_version_id": req.model_version_id,
        "desk_id": req.desk_id,
    }
    crystal_id: str | None = None
    if spine_enabled():
        try:
            crystal = adapter_for(CONFIG).crystallize(
                operation_id=req.application_id,
                risk_tier=CONFIG.default_risk_tier,
                facets=facets,
                account_id=req.desk_id,
                policy_id=CONFIG.default_policy_id,
                reserved_exposure=str(exposure),
            )
            crystal_id = crystal.crystal_id
            _record_rail_attempt(req.application_id, "RESERVED", crystal_id)
        except Exception as exc:
            logger.warning("exposure reserve failed: %s", exc)
            increment_invariant(CONFIG.name, "rail_circuit_open_total")
            raise HTTPException(status_code=409, detail="INSUFFICIENT_EXPOSURE") from exc

    try:
        outcome = _score_with_rail(req, exposure)
    except HTTPException:
        raise
    except Exception as exc:
        if crystal_id:
            try:
                adapter_for(CONFIG).strand(crystal_id, reason=str(exc))
            except Exception:
                pass
        raise

    record_credit_cohort(
        platform=CONFIG.name,
        desk_id=req.desk_id,
        model_version_id=req.model_version_id,
        application_id=req.application_id,
        score=outcome.score,
        decision=outcome.decision,
        exposure=exposure,
    )

    commit_facets = {
        **facets,
        "feature_snapshot_hash": req.feature_snapshot_hash,
        "score": outcome.score,
        "explanation_id": outcome.explanation_id,
    }

    if crystal_id and os.environ.get("FG_SPINE_ENABLED", "false").lower() == "true":
        try:
            from platforms.common.spine_adapter import CommitOutcome

            committed = str(exposure) if outcome.decision == "APPROVE" else "0"
            adapter_for(CONFIG).commit(
                CommitOutcome(
                    operation_id=req.application_id,
                    crystal_id=crystal_id,
                    facets=commit_facets,
                    outcome=outcome.decision.lower(),
                    committed_exposure=committed,
                    metadata={"explanation_id": outcome.explanation_id},
                )
            )
            _record_rail_attempt(req.application_id, outcome.decision, outcome.explanation_id)
        except Exception as exc:
            logger.exception("spine commit failed for %s", req.application_id)
            raise HTTPException(status_code=503, detail=f"spine commit failed: {exc}") from exc

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
    increment_invariant(CONFIG.name, "rail_attempt_total")
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
        increment_invariant(CONFIG.name, "rail_circuit_open_total")
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
