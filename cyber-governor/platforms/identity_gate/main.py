"""IdentityGate — crystal-bound session arm before token issuance."""
from __future__ import annotations

import os

from fastapi import FastAPI
from pydantic import BaseModel, Field

from .session_binding import SessionProfile, evaluate_session

app = FastAPI(title="identity-gate", version="0.1.0")

_DEMO_PROFILE = SessionProfile(
    user_id="alice@corp.example",
    expected_device_fingerprint="dev_fp_trusted_workstation",
    expected_ip_prefix="10.",
)


class SessionArmRequest(BaseModel):
    session_id: str
    user_id: str
    device_fingerprint: str
    client_ip: str = "10.0.1.42"
    user_agent: str = ""


class SessionArmResponse(BaseModel):
    session_id: str
    decision: str
    session_state: str
    binding_score: float
    reason: str | None = None
    crystal_id: str | None = None


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok"}


@app.post("/session/arm", response_model=SessionArmResponse)
def arm_session(request: SessionArmRequest) -> SessionArmResponse:
    result = evaluate_session(
        user_id=request.user_id,
        device_fingerprint=request.device_fingerprint,
        client_ip=request.client_ip,
        profile=_DEMO_PROFILE,
    )
    facets = {
        "user_id": request.user_id,
        "device_fingerprint": request.device_fingerprint,
        "client_ip": request.client_ip,
        "user_agent": request.user_agent,
        "session_state": result.session_state,
        "binding_score": result.binding_score,
    }
    crystal_id = _crystallize_if_spine(request.session_id, facets, approved=result.approved)
    return SessionArmResponse(
        session_id=request.session_id,
        decision="AUTHORIZED" if result.approved else "STRANDED",
        session_state=result.session_state,
        binding_score=result.binding_score,
        reason=result.reason,
        crystal_id=crystal_id,
    )


def _crystallize_if_spine(operation_id: str, facets: dict, *, approved: bool) -> str | None:
    if os.environ.get("CG_SPINE_ENABLED", "false").lower() != "true":
        return None
    try:
        from platforms.common.spine_adapter import CommitOutcome, SpineAdapter

        adapter = SpineAdapter(platform="identity_gate", spine_enabled=True)
        crystal = adapter.crystallize(
            operation_id=operation_id,
            risk_tier="critical",
            facets=facets,
            policy_id="identity-critical-us",
            account_id="tenant-default",
        )
        if approved:
            adapter.commit(
                CommitOutcome(
                    operation_id=operation_id,
                    crystal_id=crystal.crystal_id,
                    facets=facets,
                    outcome="authorized",
                )
            )
        return crystal.crystal_id
    except Exception:
        return None
