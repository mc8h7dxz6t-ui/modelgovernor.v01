"""Depreciation computation engine."""
from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from .asset_registry import Asset
from .reg_table_sync import RegTable

QUANTUM = Decimal("0.01")


def compute_monthly_charge(asset: Asset, table: RegTable) -> Decimal:
    if asset.method != "straight_line":
        raise ValueError(f"unsupported method: {asset.method}")
    annual = asset.acquisition_cost * table.straight_line_annual_pct
    monthly = (annual / Decimal("12")).quantize(QUANTUM, rounding=ROUND_HALF_UP)
    return min(monthly, asset.book_value)
