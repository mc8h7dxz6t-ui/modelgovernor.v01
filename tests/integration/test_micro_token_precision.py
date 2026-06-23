"""Micro-token money precision tests."""
from __future__ import annotations

from decimal import Decimal

from sidecar.app.money import MONEY_QUANTUM, quantize_money


def test_micro_token_cost_retains_precision() -> None:
    per_token = Decimal("0.00000015")
    thousand_tokens = quantize_money(per_token * 1000)
    assert thousand_tokens == Decimal("0.000150")
    assert thousand_tokens > Decimal("0")


def test_money_quantum_is_twelve_decimal_places() -> None:
    assert MONEY_QUANTUM == Decimal("0.000000000001")
