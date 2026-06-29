"""IncidentResponseGate — governed containment / playbook execution."""
from __future__ import annotations

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from platforms.common.platform_sdk import GovernedPlatform, increment_invariant, spine_health_payload

app = FastAPI(title="incidentresponsegate", version="0.1.0")
_GOVERNED = GovernedPlatform("incident_response_gate")

HIGH_RISK_ACTIONS = frozenset({"isolate_host", "revoke_credentials", "block_egress", "wipe_endpoint"})
ALLOWED_SEVERITIES = frozenset({"LOW", "MEDIUM", "HIGH", "CRITICAL"})


class IncidentRequest(BaseModel):
    incident_id: str
    action_type: str
    severity: str = "MEDIUM"
    playbook_id: str = "default"
    approver: str | None = None
    account_id: str = "tenant-default"


def evaluate_incident(req: IncidentRequest) -> tuple[str, str]:
    severity = req.severity.upper()
    action = req.action_type.lower().strip()
    if severity not in ALLOWED_SEVERITIES:
        increment_invariant("incident_response_gate", "ir_playbook_violation_total")
        return "DENIED", f"invalid severity: {req.severity}"
    if action in HIGH_RISK_ACTIONS and severity != "CRITICAL":
        increment_invariant("incident_response_gate", "ir_unauthorized_blocked_total")
        return "DENIED", f"action {action} requires CRITICAL severity"
    if action in HIGH_RISK_ACTIONS and not req.approver:
        increment_invariant("incident_response_gate", "ir_unauthorized_blocked_total")
        return "DENIED", "high-risk action requires approver"
    increment_invariant("incident_response_gate", "ir_authorized_total")
    return "AUTHORIZED", f"playbook:{req.playbook_id}"


@app.get("/healthz")
def healthz() -> dict:
    return spine_health_payload("incident_response_gate")


@app.get("/readyz")
def readyz() -> dict:
    return healthz()


@app.post("/incident/authorize")
def authorize(request: IncidentRequest) -> dict:
    decision, reference = evaluate_incident(request)
    facets = {
        "incident_id": request.incident_id,
        "action_type": request.action_type,
        "severity": request.severity.upper(),
        "playbook_id": request.playbook_id,
        "ir_decision": decision,
        "reference": reference,
    }
    crystal_id = _GOVERNED.govern_operation(
        f"{request.incident_id}-{request.action_type}",
        facets,
        decision=decision,
        reserve_amount="0",
        account_id=request.account_id,
        outcome=decision.lower(),
    )
    if decision != "AUTHORIZED":
        raise HTTPException(status_code=403, detail={"decision": decision, "reference": reference})
    return {"decision": decision, "crystal_id": crystal_id, "reference": reference}
