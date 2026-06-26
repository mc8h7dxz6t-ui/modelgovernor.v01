"""Property-based tests for exact-decimal money handling (institutional++)."""
from __future__ import annotations

import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from platforms.asset_ledger.asset_registry import Asset, AssetRegistry
from platforms.subledger_sync.txn_hasher import canonical_txn_hash
from platforms.wire_match.wire_schema import WireRequest


quantized_amounts = st.decimals(
    min_value=Decimal("0.01"),
    max_value=Decimal("999999999.99"),
    places=2,
    allow_nan=False,
    allow_infinity=False,
)


@given(amount=quantized_amounts)
@settings(max_examples=50)
def test_wire_amount_always_decimal_string(amount: Decimal):
    wire = WireRequest(
        wire_id="p1",
        beneficiary_name="Test",
        beneficiary_account="ACCT",
        reference="ref",
        amount=str(amount),
    )
    assert Decimal(wire.amount) == amount.quantize(Decimal("0.01"))


@given(amount=quantized_amounts)
@settings(max_examples=30)
def test_asset_registry_rejects_negative(amount: Decimal):
    reg = AssetRegistry()
    with pytest.raises(ValueError):
        reg.register(Asset("a", -amount))


@given(
    amount=quantized_amounts,
    ref=st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789", min_size=1, max_size=20),
)
@settings(max_examples=30)
def test_txn_hash_stable_under_case(amount: Decimal, ref: str):
    base = dict(
        entity_id="A",
        counterparty_id="B",
        amount=amount,
        currency="USD",
        value_date="2026-01-01",
    )
    h1 = canonical_txn_hash(**base, reference=ref.lower())
    h2 = canonical_txn_hash(**base, reference=ref.upper())
    assert h1 == h2


def test_invalid_amount_strings_rejected():
    with pytest.raises(Exception):
        WireRequest(
            wire_id="x",
            beneficiary_name="X",
            beneficiary_account="Y",
            reference="z",
            amount="1.2.3",
        )
