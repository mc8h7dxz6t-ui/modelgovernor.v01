"""Canonical money precision for sub-micro-cent LLM token pricing."""
from __future__ import annotations

from decimal import Decimal

# NUMERIC(24, 12) — supports costs like $0.00000015 per token without rounding to zero.
MONEY_QUANTUM = Decimal("0.000000000001")
MONEY_DB_PRECISION = 12


def quantize_money(value: Decimal | str | int | float | None) -> Decimal:
    return Decimal(value or 0).quantize(MONEY_QUANTUM)
