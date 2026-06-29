"""IdentityGovern — workload principal + JWT role binding gate."""
from __future__ import annotations

import hashlib
import re

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from platforms.common.platform_sdk import GovernedPlatform, increment_invariant, spine_health_payload

app = FastAPI(title="identitygovern", version="0.1.0")
_GOVERNED = GovernedPlatform("identity_govern")

_PRINCIPAL_RE = re.compile(
    r"^cluster\.local/ns/[\w-]+/sa/[\w-]+$|^[\w.@+-]+$",
)


class IdentityRequest(BaseModel):
    principal: str
    workload_sa: str
    role_set: list[str] = Field(default_factory=list)
    account_id: str = "tenant-default"


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
