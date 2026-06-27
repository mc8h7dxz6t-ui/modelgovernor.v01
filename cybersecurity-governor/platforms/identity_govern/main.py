"""IdentityGovern — workload principal + session binding gate."""
from __future__ import annotations

import hashlib
import os
import re

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from platforms.common.platform_sdk import GovernedPlatform, increment_invariant, spine_health_payload
from .session_binding import SessionProfile, evaluate_session

app = FastAPI(title="identitygovern", version="0.1.0")
_GOVERNED = GovernedPlatform("identity_govern")

_PRINCIPAL_RE = re.compile(
    r"^cluster\.local/ns/[\w-]+/sa/[\w-]+$|^[\w.@+-]+$",
)

_DEMO_PROFILE = SessionProfile(
    user_id=os.environ.get("CG_DEMO_USER_ID", "alice@corp.example"),
    expected_device_fingerprint=os.environ.get("CG_DEMO_DEVICE_FP", "dev_fp_trusted_workstation"),
    expected_ip_prefix=os.environ.get("CG_DEMO_IP_PREFIX", "10."),
)


class IdentityRequest(BaseModel):
    principal: str
    workload_sa: str
    role_set: list[str] = Field(default_factory=list)
    account_id: str = "tenant-default"


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
    reason: str | None = None
    crystal_id: str | None = None


def _role_hash(roles: list[str]) -> str:
    canonical = ",".join(sorted(r.strip().lower() for r in roles if r.strip()))
    return hashlib.sha256(canonical.encode()).hexdigest()


def evaluate_identity(req: IdentityRequest) -> tuple[str, str]:
    principal = req.principal.strip()
    workload_sa = req.workload_sa.strip()
    if not _PRINCIPAL_RE.match(principal):
        increment_invariant("identity_govern", "identity_principal_mismatch_total")
        return "VIOLATION", "invalid principal format"
    expected_suffix = workload_sa if workload_sa.startswith("sa/") else f"sa/{workload_sa}"
    if principal.endswith(expected_suffix) or principal == workload_sa:
        increment_invariant("identity_govern", "identity_verified_total")
        return "VERIFIED", f"principal matches workload:{workload_sa}"
    increment_invariant("identity_govern", "identity_principal_mismatch_total")
    if req.role_set and "security-admin" in [r.lower() for r in req.role_set]:
        increment_invariant("identity_govern", "identity_stale_role_total")
    return "VIOLATION", f"principal {principal} does not match workload {workload_sa}"


@app.get("/healthz")
def healthz() -> dict:
    return spine_health_payload("identity_govern")


@app.get("/readyz")
def readyz() -> dict:
    return healthz()


@app.post("/session/arm", response_model=SessionArmResponse)
def session_arm(request: SessionArmRequest) -> SessionArmResponse:
    """Sales SKU API — device fingerprint + IP binding; hijack → STRANDED."""
    result = evaluate_session(
        user_id=request.user_id,
        device_fingerprint=request.device_fingerprint,
        client_ip=request.client_ip,
        profile=_DEMO_PROFILE,
    )
    identity_decision = "VERIFIED" if result.session_state == "AUTHORIZED" else "VIOLATION"
    facets = {
        "session_id": request.session_id,
        "user_id": request.user_id,
        "device_fingerprint": request.device_fingerprint,
        "client_ip": request.client_ip,
        "session_state": result.session_state,
        "identity_decision": identity_decision,
        "principal": request.user_id,
        "workload_sa": request.device_fingerprint,
    }
    crystal_id = _GOVERNED.govern_operation(
        request.session_id,
        facets,
        decision=identity_decision,
        reserve_amount="0",
        outcome=result.session_state.lower(),
    )
    if not result.approved:
        raise HTTPException(
            status_code=403,
            detail={
                "session_id": request.session_id,
                "decision": "STRANDED",
                "session_state": result.session_state,
                "reason": result.reason,
            },
        )
    return SessionArmResponse(
        session_id=request.session_id,
        decision="AUTHORIZED",
        session_state=result.session_state,
        reason=result.reason,
        crystal_id=crystal_id,
    )


@app.post("/identity/verify")
def verify(request: IdentityRequest) -> dict:
    decision, reference = evaluate_identity(request)
    role_hash = _role_hash(request.role_set)
    facets = {
        "principal": request.principal,
        "workload_sa": request.workload_sa,
        "role_set_hash": role_hash,
        "identity_decision": decision,
        "reference": reference,
    }
    crystal_id = _GOVERNED.govern_operation(
        f"id-{hashlib.sha256(request.principal.encode()).hexdigest()[:16]}",
        facets,
        decision=decision,
        reserve_amount="0",
        account_id=request.account_id,
        outcome=decision.lower(),
    )
    if decision != "VERIFIED":
        raise HTTPException(status_code=403, detail={"decision": decision, "reference": reference})
    return {"decision": decision, "crystal_id": crystal_id, "role_set_hash": role_hash}
