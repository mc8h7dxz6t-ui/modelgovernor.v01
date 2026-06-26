"""AssetLedger API — runtime write-down control vs SAP FA batch modules."""
from __future__ import annotations

from decimal import Decimal

from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel

from platforms.common.platform_metrics import get_platform_metrics

from .asset_registry import Asset, AssetRegistry
from .depreciation_engine import DepreciationEngine
from .reg_table_sync import RegTableSync

app = FastAPI(title="asset_ledger", version="0.1.0")

_registry = AssetRegistry()
_reg_sync = RegTableSync()
_engine = DepreciationEngine(_registry, _reg_sync)


class RegisterAsset(BaseModel):
    asset_id: str
    book_value: str
    method: str = "straight_line"
    jurisdiction: str = "UK"


class DepreciateRequest(BaseModel):
    asset_id: str
    period: str
    jurisdiction_key: str = "UK:hmrc"


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok", "assets": len(_registry.list_assets())}


@app.get("/readyz")
def readyz() -> dict:
    return {"ready": True, "chain_valid": _engine.events.verify_chain()}


@app.get("/metrics")
def metrics() -> Response:
    return Response(content=get_platform_metrics().prometheus_text(), media_type="text/plain")


@app.post("/assets/register")
def register_asset(body: RegisterAsset) -> dict:
    try:
        value = Decimal(body.book_value)
    except Exception as exc:
        raise HTTPException(status_code=422, detail="invalid book_value") from exc
    asset = Asset(
        asset_id=body.asset_id,
        book_value=value,
        method=body.method,
        jurisdiction=body.jurisdiction,
    )
    try:
        _registry.register(asset)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"asset_id": body.asset_id, "book_value": str(value)}


@app.post("/assets/depreciate")
def depreciate(body: DepreciateRequest) -> dict:
    try:
        charge = _engine.run_period_charge(body.asset_id, body.period, body.jurisdiction_key)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "asset_id": charge.asset_id,
        "period": charge.period,
        "charge": str(charge.charge),
        "reg_table_version": charge.reg_table_version,
        "book_value_after": str(charge.book_value_after),
    }


@app.get("/assets/{asset_id}")
def get_asset(asset_id: str) -> dict:
    asset = _registry.get(asset_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="not found")
    return {
        "asset_id": asset.asset_id,
        "book_value": str(asset.book_value),
        "pinned_reg_version": _reg_sync.get_pinned(asset_id),
    }
