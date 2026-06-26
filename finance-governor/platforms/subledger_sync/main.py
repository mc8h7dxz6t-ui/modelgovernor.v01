"""SubledgerSync API."""
from __future__ import annotations

import logging
import os
from decimal import Decimal

from fastapi import FastAPI
from pydantic import BaseModel, Field

from .discrepancy_reporter import DiscrepancyReporter
from .fx_snapshot import capture_fx_rate
from .match_engine import find_mirror
from .txn_hasher import TxnRecord

logger = logging.getLogger(__name__)

app = FastAPI(title="subledger-sync", version="0.1.0")

_pending: list[TxnRecord] = []
_reporter = DiscrepancyReporter()
_matched: list[dict] = []


class TxnRequest(BaseModel):
    entity_id: str
    counterparty_id: str
    amount: str
    currency: str = "USD"
    value_date: str
    reference: str = ""


class MatchResponse(BaseModel):
    status: str
    txn_hash: str
    mirror_hash: str | None = None
    fx_hash: str | None = None
    reason: str | None = None
    crystal_id: str | None = None


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok", "pending": len(_pending), "matched": len(_matched)}


@app.post("/transactions")
def ingest(txn: TxnRequest) -> dict:
    record = TxnRecord(
        entity_id=txn.entity_id,
        counterparty_id=txn.counterparty_id,
        amount=Decimal(txn.amount),
        currency=txn.currency,
        value_date=txn.value_date,
        reference=txn.reference,
    )
    _pending.append(record)
    return {"ingested": True, "pending_count": len(_pending)}


@app.post("/match/run", response_model=MatchResponse)
def run_match(txn: TxnRequest) -> MatchResponse:
    record = TxnRecord(
        entity_id=txn.entity_id,
        counterparty_id=txn.counterparty_id,
        amount=Decimal(txn.amount),
        currency=txn.currency,
        value_date=txn.value_date,
        reference=txn.reference,
    )
    fx = capture_fx_rate(base=txn.currency, quote="USD", rate=Decimal("1.0"))
    result = find_mirror(record, _pending, fx)
    if result.matched:
        _matched.append({"txn_hash": result.txn_hash, "mirror_hash": result.mirror_hash, "fx_hash": result.fx_hash})
        crystal_id = _crystallize_match(record, result)
        return MatchResponse(
            status="MATCHED",
            txn_hash=result.txn_hash,
            mirror_hash=result.mirror_hash,
            fx_hash=result.fx_hash,
            crystal_id=crystal_id,
        )
    _reporter.emit(txn_hash=result.txn_hash, reason=result.reason or "UNMATCHED", metadata={"entity": txn.entity_id})
    return MatchResponse(status="DISCREPANCY", txn_hash=result.txn_hash, reason=result.reason)


@app.get("/discrepancies")
def discrepancies(limit: int = 20) -> list:
    return _reporter.list_recent(limit)


def _crystallize_match(record: TxnRecord, result) -> str | None:
    if os.environ.get("FG_SPINE_ENABLED", "false").lower() != "true":
        return None
    try:
        from platforms.common.spine_adapter import SpineAdapter

        op_id = f"ic-{result.txn_hash[:16]}"
        facets = {
            "txn_hash": result.txn_hash,
            "mirror_hash": result.mirror_hash,
            "fx_hash": result.fx_hash,
            "entity_id": record.entity_id,
        }
        adapter = SpineAdapter(platform="subledger_sync", spine_enabled=True)
        crystal = adapter.crystallize(operation_id=op_id, risk_tier="standard", facets=facets)
        return crystal.crystal_id
    except Exception as exc:
        logger.warning("spine crystallize failed: %s", exc)
        return None
