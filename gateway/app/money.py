"""Canonical money precision for gateway provider billing."""
from __future__ import annotations

from decimal import Decimal

MONEY_QUANTUM = Decimal("0.000000000001")


def quantize_money(value: Decimal | str | int | float | None) -> Decimal:
    return Decimal(value or 0).quantize(MONEY_QUANTUM)
