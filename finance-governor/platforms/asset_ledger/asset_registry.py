"""Asset master registry."""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any


@dataclass
class Asset:
    asset_id: str
    description: str
    book_value: Decimal
    acquisition_cost: Decimal
    method: str
    jurisdiction: str
    useful_life_months: int
    accumulated_depreciation: Decimal = Decimal("0")


class AssetRegistry:
    def __init__(self) -> None:
        self._assets: dict[str, Asset] = {}

    def register(self, asset: Asset) -> None:
        if asset.book_value < 0:
            raise ValueError("book value cannot be negative")
        self._assets[asset.asset_id] = asset

    def get(self, asset_id: str) -> Asset | None:
        return self._assets.get(asset_id)

    def list_all(self) -> list[Asset]:
        return list(self._assets.values())

    def apply_depreciation(self, asset_id: str, charge: Decimal, *, period: str) -> dict[str, Any]:
        asset = self._assets[asset_id]
        charge = min(charge, asset.book_value)
        asset.accumulated_depreciation += charge
        asset.book_value -= charge
        return {
            "asset_id": asset_id,
            "period": period,
            "charge": str(charge),
            "book_value": str(asset.book_value),
        }
