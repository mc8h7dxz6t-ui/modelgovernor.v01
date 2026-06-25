"""Depreciation engine — programmatic write-down with reg table version pinning."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from platforms.common.event_store import AppendOnlyEventStore
from platforms.common.platform_metrics import get_platform_metrics

from .asset_registry import AssetRegistry
from .reg_table_sync import RegTableSync


@dataclass(frozen=True)
class DepreciationCharge:
    asset_id: str
    period: str
    charge: Decimal
    reg_table_version: str
    book_value_after: Decimal


class DepreciationEngine:
    def __init__(self, registry: AssetRegistry, reg_sync: RegTableSync) -> None:
        self._registry = registry
        self._reg_sync = reg_sync
        self._charged_periods: set[tuple[str, str]] = set()
        self._events = AppendOnlyEventStore()

    @property
    def events(self) -> AppendOnlyEventStore:
        return self._events

    def run_period_charge(
        self,
        asset_id: str,
        period: str,
        jurisdiction_key: str,
    ) -> DepreciationCharge:
        metrics = get_platform_metrics()
        key = (asset_id, period)
        if key in self._charged_periods:
            metrics.increment("depreciation_duplicate_period_total")
            raise ValueError(f"duplicate charge for {asset_id} period {period}")

        asset = self._registry.get(asset_id)
        if asset is None:
            raise ValueError(f"unknown asset: {asset_id}")

        table = self._reg_sync.pin_version(asset_id, jurisdiction_key)
        pinned = self._reg_sync.get_pinned(asset_id)
        if pinned != table.version:
            metrics.increment("reg_table_version_mismatch_total")
            raise ValueError("reg_table_version mismatch")

        charge = (asset.book_value * table.straight_line_rate / Decimal(12)).quantize(Decimal("0.01"))
        new_value = asset.book_value - charge
        if new_value < 0:
            metrics.increment("negative_book_value_total")
            charge = asset.book_value
            new_value = Decimal("0")

        self._registry.update_book_value(asset_id, new_value)
        self._charged_periods.add(key)
        result = DepreciationCharge(
            asset_id=asset_id,
            period=period,
            charge=charge,
            reg_table_version=table.version,
            book_value_after=new_value,
        )
        self._events.append(
            platform="asset_ledger",
            event_type="DEPRECIATION",
            operation_id=f"{asset_id}:{period}",
            payload={
                "charge": str(charge),
                "reg_table_version": table.version,
                "book_value_after": str(new_value),
            },
        )
        return result
