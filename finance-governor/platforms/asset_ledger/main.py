"""AssetLedger API."""
from __future__ import annotations

import logging
import os
from decimal import Decimal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from .asset_registry import Asset, AssetRegistry
from .depreciation_engine import compute_monthly_charge
from .reg_table_sync import get_table

logger = logging.getLogger(__name__)

app = FastAPI(title="asset-ledger", version="0.1.0")

_registry = AssetRegistry()
_events: list[dict] = []
_charged_periods: set[tuple[str, str]] = set()


class AssetCreate(BaseModel):
    asset_id: str
    description: str
    acquisition_cost: str
    book_value: str | None = None
    method: str = "straight_line"
    jurisdiction: str = "US"
    useful_life_months: int = 60


class DepreciationRun(BaseModel):
    period: str


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok", "assets": len(_registry.list_all())}


@app.post("/assets")
def create_asset(body: AssetCreate) -> dict:
    cost = Decimal(body.acquisition_cost)
    book = Decimal(body.book_value) if body.book_value else cost
    asset = Asset(
        asset_id=body.asset_id,
        description=body.description,
        book_value=book,
        acquisition_cost=cost,
        method=body.method,
        jurisdiction=body.jurisdiction,
        useful_life_months=body.useful_life_months,
    )
    _registry.register(asset)
    return {"asset_id": body.asset_id, "book_value": str(book)}


@app.get("/assets/{asset_id}")
def get_asset(asset_id: str) -> dict:
    asset = _registry.get(asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="asset not found")
    return {
        "asset_id": asset.asset_id,
        "book_value": str(asset.book_value),
        "accumulated_depreciation": str(asset.accumulated_depreciation),
        "jurisdiction": asset.jurisdiction,
    }


@app.post("/depreciation/run")
def run_depreciation(body: DepreciationRun) -> dict:
    table = get_table("US")
    results = []
    for asset in _registry.list_all():
        key = (asset.asset_id, body.period)
        if key in _charged_periods:
            continue
        tbl = get_table(asset.jurisdiction)
        charge = compute_monthly_charge(asset, tbl)
        if charge <= 0:
            continue
        row = _registry.apply_depreciation(asset.asset_id, charge, period=body.period)
        _charged_periods.add(key)
        row["reg_table_version"] = tbl.version
        _events.append(row)
        crystal_id = _crystallize_depreciation(asset.asset_id, body.period, row, tbl.version)
        row["crystal_id"] = crystal_id
        results.append(row)
    return {"period": body.period, "charges": results, "reg_table_version": table.version}


@app.get("/events")
def list_events(limit: int = 20) -> list:
    return list(reversed(_events[-limit:]))


def _crystallize_depreciation(asset_id: str, period: str, row: dict, table_version: str) -> str | None:
    if os.environ.get("FG_SPINE_ENABLED", "false").lower() != "true":
        return None
    try:
        from platforms.common.spine_adapter import CommitOutcome, SpineAdapter

        op_id = f"dep-{asset_id}-{period}"
        facets = {"asset_id": asset_id, "period": period, "charge": row["charge"], "reg_table_version": table_version}
        adapter = SpineAdapter(platform="asset_ledger", spine_enabled=True)
        crystal = adapter.crystallize(operation_id=op_id, risk_tier="standard", facets=facets)
        adapter.commit(
            CommitOutcome(
                operation_id=op_id,
                crystal_id=crystal.crystal_id,
                facets=facets,
                outcome="depreciated",
                committed_exposure=row["charge"],
            )
        )
        return crystal.crystal_id
    except Exception as exc:
        logger.warning("spine crystallize failed: %s", exc)
        return None
