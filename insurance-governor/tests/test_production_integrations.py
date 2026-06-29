"""Production integration adapter tests."""
from __future__ import annotations

import os
from decimal import Decimal
from unittest import mock

import pytest

from platforms.claim_gate.payment_rail import reset_payment_store, submit_payment
from platforms.common.integrations.bank_rail import dispatch_payment, payment_rail_mode
from platforms.common.integrations.oracle_providers import oracle_feed_mode
from platforms.common.persistence.payment_types import PaymentInstruction, PaymentStatus
from platforms.parametric_oracle.oracle_feed import fetch_oracle_feed, fetch_usgs_earthquake_mock


def test_payment_stub_rail_completes():
    instr = PaymentInstruction(
        payment_id="pay_test_1",
        claim_id="c1",
        idempotency_key="idem-1",
        amount=Decimal("100"),
        currency="USD",
        payee_id="p1",
        status=PaymentStatus.PENDING,
    )
    with mock.patch.dict(os.environ, {"PAYMENT_RAIL_MODE": "stub"}, clear=False):
        result = dispatch_payment(instr)
    assert result.status == PaymentStatus.COMPLETED
    assert result.rail == "ach_stub"


def test_payment_idempotency_memory_store():
    reset_payment_store()
    first = submit_payment(
        claim_id="c-idem",
        amount=Decimal("50"),
        currency="USD",
        payee_id="payee",
        idempotency_key="unique-key-1",
        gate_decision="APPROVED",
        crystal_id="crystal-abc",
    )
    second = submit_payment(
        claim_id="c-idem",
        amount=Decimal("50"),
        currency="USD",
        payee_id="payee",
        idempotency_key="unique-key-1",
        gate_decision="APPROVED",
        crystal_id="crystal-abc",
    )
    assert first.payment_id == second.payment_id


def test_oracle_mock_feed_default():
    with mock.patch.dict(os.environ, {"ORACLE_FEED_MODE": "mock"}, clear=False):
        reading = fetch_oracle_feed("usgs-feed")
    assert reading.metric_value == Decimal("7.2")


def test_oracle_live_mode_calls_provider():
    with mock.patch.dict(os.environ, {"ORACLE_FEED_MODE": "live"}, clear=False):
        with mock.patch(
            "platforms.parametric_oracle.oracle_feed.resolve_live_feed",
            return_value=fetch_usgs_earthquake_mock(),
        ) as resolver:
            reading = fetch_oracle_feed("usgs-live")
    resolver.assert_called_once_with("usgs-live")
    assert reading.source == "usgs-feed"


def test_integration_mode_env_defaults():
    assert payment_rail_mode() in ("stub", "fednow", "clearinghouse", "ach")
    assert oracle_feed_mode() in ("mock", "live")
