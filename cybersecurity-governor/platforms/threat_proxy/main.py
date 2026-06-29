"""ThreatProxy — pre-dispatch threat score gate (blocks before exfiltration path)."""
from __future__ import annotations

import os
from decimal import Decimal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from platforms.common.platform_sdk import GovernedPlatform, increment_invariant, spine_health_payload

app = FastAPI(title="threatproxy", version="0.1.0")
_GOVERNED = GovernedPlatform("threat_proxy")


class ThreatRequest(BaseModel):
    request_id: str
    payload_entropy: float = 0.0
    anomaly_signals: list[str] = Field(default_factory=list)
    data_class: str = "internal"
    account_id: str = "tenant-default"


def _threshold() -> Decimal:
    return Decimal(os.environ.get("THREAT_SCORE_THRESHOLD", "0.75"))


def score_threat(req: ThreatRequest) -> tuple[Decimal, str]:
    base = Decimal("0.1")
    if req.data_class.lower() in ("secret", "pii", "pci"):
        base += Decimal("0.25")
    base += Decimal(str(min(req.payload_entropy, 1.0))) * Decimal("0.3")
    signal_weight = {
        "prompt_injection": Decimal("0.35"),
        "tool_abuse": Decimal("0.4"),
        "credential_spray": Decimal("0.5"),
        "lateral_movement": Decimal("0.45"),
        "exfil_pattern": Decimal("0.55"),
    }
    for sig in req.anomaly_signals:
        base += signal_weight.get(sig.lower(), Decimal("0.15"))
    return min(base, Decimal("1.0")), ",".join(req.anomaly_signals) or "none"


@app.get("/healthz")
def healthz() -> dict:
    return spine_health_payload("threat_proxy")


@app.get("/readyz")
def readyz() -> dict:
    return healthz()


@app.post("/threat/score")
def score(request: ThreatRequest) -> dict:
    threat_score, signals = score_threat(request)
    threshold = _threshold()
    decision = "CLEARED" if threat_score < threshold else "BLOCKED"
    if decision == "BLOCKED":
        increment_invariant("threat_proxy", "threat_blocked_total")
        increment_invariant("threat_proxy", "threat_high_risk_total")
    else:
        increment_invariant("threat_proxy", "threat_cleared_total")
    facets = {
        "request_id": request.request_id,
        "threat_score": str(threat_score),
        "threshold": str(threshold),
        "signals": signals,
        "threat_decision": decision,
    }
    crystal_id = _GOVERNED.govern_operation(
        request.request_id,
        facets,
        decision=decision,
        reserve_amount="0",
        account_id=request.account_id,
        outcome=decision.lower(),
    )
    if decision != "CLEARED":
        raise HTTPException(status_code=403, detail={"threat_score": str(threat_score), "decision": decision})
    return {"threat_score": str(threat_score), "decision": decision, "crystal_id": crystal_id}
