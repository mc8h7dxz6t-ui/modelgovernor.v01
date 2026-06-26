"""Regulatory depreciation table sync."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class RegTable:
    jurisdiction: str
    version: str
    straight_line_annual_pct: Decimal


_TABLES: dict[str, RegTable] = {
    "US": RegTable(jurisdiction="US", version="irs-2024-v1", straight_line_annual_pct=Decimal("0.20")),
    "UK": RegTable(jurisdiction="UK", version="hmrc-2024-v1", straight_line_annual_pct=Decimal("0.18")),
}


def get_table(jurisdiction: str) -> RegTable:
    key = jurisdiction.upper()
    if key not in _TABLES:
        raise KeyError(f"unknown jurisdiction: {jurisdiction}")
    return _TABLES[key]
