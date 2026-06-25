"""CreditGovern API — reserve-before-score runtime governance vs ValidMind/Fiddler post-hoc."""
from __future__ import annotations

from decimal import Decimal

from fastapi import FastAPI, Response
from pydantic import BaseModel

from platforms.common.platform_metrics import get_platform_metrics

from .exposure_ledger import ExposureLedger
from .score_gate import PolicyRegistry, ScoreGate

app = FastAPI(title="credit_govern", version="0.1.0")

_ledger = ExposureLedger()
_ledger.ensure_desk("desk-consumer", Decimal("1000000"))
_policy = PolicyRegistry(
    approved_model_version="credit-v3.2.1",
    max_auto_approve_amount=Decimal("25000"),
)
_gate = ScoreGate(_ledger, _policy)


class DecisionRequest(BaseModel):
    application_id: str
    desk_id: str = "desk-consumer"
    exposure_amount: str
    model_version: str
    feature_snapshot_hash: str


class DeskSetup(BaseModel):
    desk_id: str
    cap_amount: str


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok"}


@app.get("/metrics")
def metrics() -> Response:
    return Response(content=get_platform_metrics().prometheus_text(), media_type="text/plain")


@app.post("/admin/desks")
def setup_desk(body: DeskSetup) -> dict:
    desk = _ledger.ensure_desk(body.desk_id, Decimal(body.cap_amount))
    return {"desk_id": desk.desk_id, "cap_amount": str(desk.cap_amount)}


@app.post("/governed/decision")
def governed_decision(body: DecisionRequest) -> dict:
    return _gate.governed_decision(
        application_id=body.application_id,
        desk_id=body.desk_id,
        exposure_amount=Decimal(body.exposure_amount),
        model_version=body.model_version,
        feature_snapshot_hash=body.feature_snapshot_hash,
    )


@app.get("/internal/exposure/{desk_id}")
def exposure_snapshot(desk_id: str) -> dict:
    return _ledger.snapshot(desk_id)


@app.get("/internal/events/recent")
def recent_events(limit: int = 20) -> dict:
    events = _gate.events.recent(limit)
    return {
        "events": [{"event_type": e.event_type, "operation_id": e.operation_id, "payload": e.payload} for e in events],
        "chain_valid": _gate.events.verify_chain(),
    }
