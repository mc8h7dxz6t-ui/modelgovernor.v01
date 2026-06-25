"""AssetLedger — asset registry with book value tracking."""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal


@dataclass
class Asset:
    asset_id: str
    book_value: Decimal
    method: str = "straight_line"
    jurisdiction: str = "UK"


class AssetRegistry:
    def __init__(self) -> None:
        self._assets: dict[str, Asset] = {}

    def register(self, asset: Asset) -> None:
        if asset.book_value < 0:
            raise ValueError("book_value cannot be negative")
        self._assets[asset.asset_id] = asset

    def get(self, asset_id: str) -> Asset | None:
        return self._assets.get(asset_id)

    def update_book_value(self, asset_id: str, new_value: Decimal) -> None:
        if new_value < 0:
            raise ValueError("book_value cannot be negative")
        asset = self._assets[asset_id]
        asset.book_value = new_value

    def list_assets(self) -> list[Asset]:
        return list(self._assets.values())
