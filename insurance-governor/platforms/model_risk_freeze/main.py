"""ModelRiskFreeze — E&O / Cyber loss control for claims and pricing AI."""
from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from platforms.common.platform_metrics import render_prometheus_text

from platforms.common.platform_sdk import GovernedPlatform, increment_invariant, spine_health_payload

from .freeze_controller import ModelRiskController, VersionRegistry, evaluate_inference

app = FastAPI(title="modelriskfreeze", version="0.1.0")
_GOVERNED = GovernedPlatform("model_risk_freeze")

_controllers: dict[str, ModelRiskController] = {}
_registries: dict[str, VersionRegistry] = {
    "US": VersionRegistry(approved_version="claims-model-v3.2.1", product_line="claims_triage_us"),
    "UK": VersionRegistry(approved_version="claims-model-uk-v2.1.0", product_line="claims_triage_uk"),
}


def _controller(jurisdiction: str) -> ModelRiskController:
    key = jurisdiction.upper()
    if key not in _controllers:
        _controllers[key] = ModelRiskController()
    return _controllers[key]


def _registry(jurisdiction: str) -> VersionRegistry:
    key = jurisdiction.upper()
    return _registries.get(key, _registries["US"])


class InferenceRequest(BaseModel):
    inference_id: str
    runtime_version: str
    jurisdiction: str = "US"
    model_use: str = "claims_triage"


class VersionUpdate(BaseModel):
    approved_version: str
    jurisdiction: str = "US"


@app.get("/healthz")
def healthz() -> dict:
    return spine_health_payload("model_risk_freeze")


@app.get("/status")
def status(jurisdiction: str = "US") -> dict:
    ctrl = _controller(jurisdiction)
    reg = _registry(jurisdiction)
    return {
        "freeze_state": ctrl.state.value,
        "reason": ctrl.reason,
        "approved_version": reg.approved_version,
        "jurisdiction": jurisdiction.upper(),
        "blocked_inferences": ctrl.blocked_inferences,
        "warranty_impact": "FROZEN blocks claim_gate and indemnity_pay_gate via mesh",
    }


@app.post("/admin/approved-version")
def set_approved_version(body: VersionUpdate) -> dict:
    key = body.jurisdiction.upper()
    _registries[key] = VersionRegistry(approved_version=body.approved_version)
    _controller(key).unfreeze()
    return {"approved_version": body.approved_version, "jurisdiction": key}


@app.get("/metrics", response_class=PlainTextResponse)
def metrics() -> str:
    return render_prometheus_text("model_risk_freeze")


@app.post("/inference/evaluate")
def evaluate(body: InferenceRequest) -> dict:
    ctrl = _controller(body.jurisdiction)
    reg = _registry(body.jurisdiction)
    result = evaluate_inference(
        inference_id=body.inference_id,
        runtime_version=body.runtime_version,
        registry=reg,
        controller=ctrl,
        jurisdiction=body.jurisdiction,
    )
    if result.reason and result.reason.startswith("version_mismatch"):
        increment_invariant("model_risk_freeze", "version_mismatch_freeze_total")
    elif not result.allowed:
        increment_invariant("model_risk_freeze", "frozen_inference_blocked_total")
    else:
        increment_invariant("model_risk_freeze", "inference_allowed_total")
    facets = {
        "inference_id": body.inference_id,
        "freeze_state": result.freeze_state,
        "model_version": body.runtime_version,
        "approved_version": reg.approved_version,
        "model_use": body.model_use,
        "jurisdiction": body.jurisdiction.upper(),
    }
    # Crystallize only — FROZEN stays non-terminal to enforce mesh warranty blocks
    crystal_id = _GOVERNED.govern_operation(
        body.inference_id,
        facets,
        decision=result.decision,
        reserve_amount="0",
        outcome="inference",
    )
    if not result.allowed:
        raise HTTPException(status_code=403, detail=result.reason or "MODEL_FROZEN")
    return {
        "inference_id": body.inference_id,
        "decision": result.decision,
        "freeze_state": result.freeze_state,
        "crystal_id": crystal_id,
    }
