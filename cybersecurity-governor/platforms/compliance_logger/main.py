"""ComplianceLogger — immutable SOC2/NIST control evidence sealing."""
from __future__ import annotations

import hashlib
import json

from fastapi import FastAPI
from pydantic import BaseModel, Field

from platforms.common.platform_sdk import GovernedPlatform, increment_invariant, spine_health_payload

app = FastAPI(title="compliancelogger", version="0.1.0")
_GOVERNED = GovernedPlatform("compliance_logger")


class ComplianceEvent(BaseModel):
    framework: str
    control_id: str
    evidence: dict = Field(default_factory=dict)
    account_id: str = "tenant-default"


def evidence_hash(framework: str, control_id: str, evidence: dict) -> str:
    payload = json.dumps(
        {"framework": framework, "control_id": control_id, "evidence": evidence},
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode()).hexdigest()


@app.get("/healthz")
def healthz() -> dict:
    return spine_health_payload("compliance_logger")


@app.get("/readyz")
def readyz() -> dict:
    return healthz()


@app.post("/compliance/log")
def log_event(request: ComplianceEvent) -> dict:
    ev_hash = evidence_hash(request.framework, request.control_id, request.evidence)
    facets = {
        "framework": request.framework.upper(),
        "control_id": request.control_id,
        "evidence_hash": ev_hash,
        "compliance_decision": "LOGGED",
    }
    op_id = f"{request.framework}-{request.control_id}-{ev_hash[:12]}"
    crystal_id = _GOVERNED.govern_operation(
        op_id,
        facets,
        decision="LOGGED",
        reserve_amount="0",
        account_id=request.account_id,
        outcome="logged",
    )
    increment_invariant("compliance_logger", "compliance_event_logged_total")
    increment_invariant("compliance_logger", "compliance_export_ready_total")
    return {
        "framework": request.framework,
        "control_id": request.control_id,
        "evidence_hash": ev_hash,
        "crystal_id": crystal_id,
    }
