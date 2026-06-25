"""SubledgerSync API."""
from __future__ import annotations

import logging
from decimal import Decimal

from fastapi import FastAPI
from pydantic import BaseModel

from platforms.common.platform_configs import SUBLEDGER_CONFIG
from platforms.common.platform_sdk import create_platform_app, increment_invariant
from platforms.common.platform_store import get_subledger_store, reset_all_stores
from platforms.common.spine_helpers import crystallize_and_commit

from .fx_snapshot import capture_fx_rate
from .match_engine import find_mirror
from .txn_hasher import TxnRecord, txn_hash

logger = logging.getLogger(__name__)

CONFIG = SUBLEDGER_CONFIG
_store = get_subledger_store()

app = create_platform_app(
    CONFIG,
    ready_check=lambda: _store.ready(),
    extra_health=lambda: {"pending": _store.count_pending(), "matched": _store.count_matched()},
)


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


def _to_record(txn: TxnRequest) -> TxnRecord:
    return TxnRecord(
        entity_id=txn.entity_id,
        counterparty_id=txn.counterparty_id,
        amount=Decimal(txn.amount),
        currency=txn.currency,
        value_date=txn.value_date,
        reference=txn.reference,
    )


def _pending_as_records() -> list[TxnRecord]:
    records = []
    for row in _store.list_pending_records():
        records.append(
            TxnRecord(
                entity_id=row["entity_id"],
                counterparty_id=row["counterparty_id"],
                amount=Decimal(str(row["amount"])),
                currency=row["currency"],
                value_date=row["value_date"],
                reference=row.get("reference", ""),
            )
        )
    return records


@app.post("/transactions")
def ingest(txn: TxnRequest) -> dict:
    record = _to_record(txn)
    th = txn_hash(record)
    payload = {
        "entity_id": txn.entity_id,
        "counterparty_id": txn.counterparty_id,
        "amount": txn.amount,
        "currency": txn.currency,
        "value_date": txn.value_date,
        "reference": txn.reference,
    }
    ingested = _store.ingest(txn_hash=th, record=payload)
    return {"ingested": ingested, "txn_hash": th, "pending_count": _store.count_pending()}


@app.post("/match/run", response_model=MatchResponse)
def run_match(txn: TxnRequest) -> MatchResponse:
    record = _to_record(txn)
    try:
        fx = capture_fx_rate(base=txn.currency, quote="USD", rate=Decimal("1.0"))
    except Exception:
        increment_invariant(CONFIG.name, "fx_snapshot_failed_total")
        raise
    pending = _pending_as_records()
    result = find_mirror(record, pending, fx)
    if result.matched:
        _store.mark_matched(txn_hash=result.txn_hash, mirror_hash=result.mirror_hash or "", fx_hash=result.fx_hash or "")
        increment_invariant(CONFIG.name, "ic_matched_total")
        op_id = f"ic-{result.txn_hash[:16]}"
        facets = {
            "txn_hash": result.txn_hash,
            "mirror_hash": result.mirror_hash,
            "fx_hash": result.fx_hash,
            "entity_id": record.entity_id,
            "counterparty_id": record.counterparty_id,
            "amount": txn.amount,
            "currency": txn.currency,
        }
        crystal_id = crystallize_and_commit(
            CONFIG,
            op_id,
            facets,
            committed_exposure="0",
            outcome="matched",
        )
        return MatchResponse(
            status="MATCHED",
            txn_hash=result.txn_hash,
            mirror_hash=result.mirror_hash,
            fx_hash=result.fx_hash,
            crystal_id=crystal_id,
        )
    reason = result.reason or "UNMATCHED"
    _store.record_discrepancy(txn_hash=result.txn_hash, reason=reason, metadata={"entity": txn.entity_id})
    return MatchResponse(status="DISCREPANCY", txn_hash=result.txn_hash, reason=reason)


@app.get("/discrepancies")
def discrepancies(limit: int = 20) -> list:
    return _store.list_discrepancies(limit)


@app.get("/internal/orphans")
def orphans() -> dict:
    count = _store.count_orphans()
    if count:
        increment_invariant(CONFIG.name, "ic_orphan_detected_total", count)
    return {"orphan_pending": count}


def reset_state() -> None:
    reset_all_stores()
