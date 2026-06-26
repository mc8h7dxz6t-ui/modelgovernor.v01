"""Regulatory table sync — pinned version per charge (vs CCH reporting-only)."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class RegTable:
    jurisdiction: str
    version: str
    effective_date: str
    straight_line_rate: Decimal


class RegTableSync:
    def __init__(self) -> None:
        self._tables: dict[str, RegTable] = {
            "UK:hmrc": RegTable("UK", "hmrc-2026-q1", "2026-01-01", Decimal("0.20")),
            "US:irs": RegTable("US", "irs-2026-q1", "2026-01-01", Decimal("0.25")),
        }
        self._pinned: dict[str, str] = {}

    def pin_version(self, asset_id: str, jurisdiction_key: str) -> RegTable:
        table = self._tables[jurisdiction_key]
        self._pinned[asset_id] = table.version
        return table

    def get_pinned(self, asset_id: str) -> str | None:
        return self._pinned.get(asset_id)

    def get_table(self, jurisdiction_key: str) -> RegTable:
        return self._tables[jurisdiction_key]
