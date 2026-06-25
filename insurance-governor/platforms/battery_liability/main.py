"""BatteryLiability — EV battery degradation and thermal event liability."""
from __future__ import annotations

from decimal import Decimal

from fastapi import FastAPI
from pydantic import BaseModel

from platforms.common.platform_sdk import GovernedPlatform, spine_health_payload

from .battery_gate import evaluate_battery_liability

app = FastAPI(title="batteryliability", version="0.1.0")
_GOVERNED = GovernedPlatform("battery_liability")


class BatteryRequest(BaseModel):
    claim_id: str
    state_of_health_pct: float
    thermal_event: bool = False
    mileage: int = 0
    repair_estimate: str = "0"


@app.get("/healthz")
def healthz() -> dict:
    return spine_health_payload("battery_liability")


@app.post("/battery/evaluate")
def evaluate(request: BatteryRequest) -> dict:
    result = evaluate_battery_liability(
        claim_id=request.claim_id,
        state_of_health_pct=request.state_of_health_pct,
        thermal_event=request.thermal_event,
        mileage=request.mileage,
        repair_estimate=Decimal(request.repair_estimate),
    )
    facets = {
        "claim_id": request.claim_id,
        "state_of_health_pct": request.state_of_health_pct,
        "thermal_event": request.thermal_event,
        "battery_decision": result.decision,
        "liability_amount": str(result.liability_amount),
    }
    crystal_id = _GOVERNED.govern_operation(
        request.claim_id,
        facets,
        decision=result.decision,
        reserve_amount=str(result.liability_amount) if result.approved else "0",
        outcome="battery_liability",
    )
    return {"decision": result.decision, "crystal_id": crystal_id, "reason": result.reason}
