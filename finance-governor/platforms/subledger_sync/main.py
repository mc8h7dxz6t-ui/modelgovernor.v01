"""SubledgerSync API — real-time IC match at clear with FX snapshot hash."""
from __future__ import annotations

from decimal import Decimal

from fastapi import FastAPI, Response
from pydantic import BaseModel

from platforms.common.event_store import AppendOnlyEventStore
from platforms.common.platform_metrics import get_platform_metrics

from .fx_snapshot import capture_fx_snapshot
from .match_engine import IcTransaction, MatchEngine
from .txn_hasher import canonical_txn_hash

app = FastAPI(title="subledger_sync", version="0.1.0")

_engine = MatchEngine()
_events = AppendOnlyEventStore()


class IngestRequest(BaseModel):
    entity_id: str
    counterparty_id: str
    amount: str
    currency: str
    reference: str
    value_date: str
    fx_rate: str | None = None
    fx_base: str = "USD"
    fx_quote: str = "EUR"


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok", "orphans": _engine.orphan_count()}


@app.get("/metrics")
def metrics() -> Response:
    return Response(content=get_platform_metrics().prometheus_text(), media_type="text/plain")


@app.post("/ic/ingest")
def ingest(body: IngestRequest) -> dict:
    amount = Decimal(body.amount)
    txn_hash = canonical_txn_hash(
        entity_id=body.entity_id,
        counterparty_id=body.counterparty_id,
        amount=amount,
        currency=body.currency,
        reference=body.reference,
        value_date=body.value_date,
    )
    txn = IcTransaction(
        txn_hash=txn_hash,
        entity_id=body.entity_id,
        counterparty_id=body.counterparty_id,
        amount=amount,
        currency=body.currency,
    )
    fx = None
    if body.fx_rate:
        fx = capture_fx_snapshot(
            base_currency=body.fx_base,
            quote_currency=body.fx_quote,
            rate=Decimal(body.fx_rate),
        )
    result = _engine.ingest(txn)
    if result is None:
        return {"status": "PENDING", "txn_hash": txn_hash}

    payload = {
        "matched": result.matched,
        "pair_id": result.pair_id,
        "fx_snapshot_hash": result.fx_snapshot_hash,
        "reason": result.reason,
    }
    if fx and result.matched:
        payload["fx_snapshot_hash"] = fx.snapshot_hash

    _events.append(
        platform="subledger_sync",
        event_type="MATCH" if result.matched else "MISMATCH",
        operation_id=txn_hash,
        payload=payload,
    )
    return {"status": "MATCHED" if result.matched else "REJECTED", **payload}


@app.post("/ic/sweep")
def sweep() -> dict:
    stranded = _engine.sweep_orphans()
    return {"stranded_orphans": stranded}


@app.get("/internal/events/recent")
def recent_events(limit: int = 20) -> dict:
    events = _events.recent(limit)
    return {"events": [{"event_type": e.event_type, "operation_id": e.operation_id, "payload": e.payload} for e in events]}
