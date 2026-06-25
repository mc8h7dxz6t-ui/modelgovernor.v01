"""AssetLedger API."""
from __future__ import annotations

import logging
from decimal import Decimal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from platforms.common.platform_configs import ASSET_LEDGER_CONFIG
from platforms.common.platform_sdk import create_platform_app
from platforms.common.platform_store import get_asset_store, reset_all_stores
from platforms.common.spine_helpers import crystallize_and_commit

from .asset_registry import Asset
from .depreciation_engine import compute_monthly_charge
from .reg_table_sync import get_table

logger = logging.getLogger(__name__)

CONFIG = ASSET_LEDGER_CONFIG
_store = get_asset_store()

app = create_platform_app(
    CONFIG,
    ready_check=lambda: _store.ready(),
    extra_health=lambda: {"assets": len(_store.list_assets())},
)


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


@app.post("/assets")
def create_asset(body: AssetCreate) -> dict:
    cost = Decimal(body.acquisition_cost)
    book = Decimal(body.book_value) if body.book_value else cost
    try:
        _store.register_asset(
            {
                "asset_id": body.asset_id,
                "description": body.description,
                "acquisition_cost": str(cost),
                "book_value": str(book),
                "accumulated_depreciation": "0",
                "method": body.method,
                "jurisdiction": body.jurisdiction,
                "useful_life_months": body.useful_life_months,
            }
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"asset_id": body.asset_id, "book_value": str(book)}


@app.get("/assets/{asset_id}")
def get_asset(asset_id: str) -> dict:
    asset = _store.get_asset(asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="asset not found")
    return {
        "asset_id": asset["asset_id"],
        "book_value": str(asset["book_value"]),
        "accumulated_depreciation": str(asset["accumulated_depreciation"]),
        "jurisdiction": asset["jurisdiction"],
    }


@app.post("/depreciation/run")
def run_depreciation(body: DepreciationRun) -> dict:
    table = get_table("US")
    results = []
    for row in _store.list_assets():
        asset = Asset(
            asset_id=row["asset_id"],
            description=row["description"],
            book_value=Decimal(str(row["book_value"])),
            acquisition_cost=Decimal(str(row["acquisition_cost"])),
            method=row["method"],
            jurisdiction=row["jurisdiction"],
            useful_life_months=int(row["useful_life_months"]),
            accumulated_depreciation=Decimal(str(row["accumulated_depreciation"])),
        )
        tbl = get_table(asset.jurisdiction)
        charge = compute_monthly_charge(asset, tbl)
        if charge <= 0:
            continue
        charge_row = _store.apply_charge(
            asset_id=asset.asset_id,
            period=body.period,
            charge=str(charge),
            reg_table_version=tbl.version,
            crystal_id=None,
        )
        if not charge_row:
            continue
        op_id = f"dep-{asset.asset_id}-{body.period}"
        facets = {
            "asset_id": asset.asset_id,
            "period": body.period,
            "charge": charge_row["charge"],
            "reg_table_version": tbl.version,
        }
        crystal_id = crystallize_and_commit(
            CONFIG,
            op_id,
            facets,
            committed_exposure=charge_row["charge"],
            outcome="depreciated",
        )
        charge_row["crystal_id"] = crystal_id
        results.append(charge_row)
    return {"period": body.period, "charges": results, "reg_table_version": table.version}


@app.get("/events")
def list_events(limit: int = 20) -> list:
    return _store.list_events(limit)


def reset_state() -> None:
    reset_all_stores()
