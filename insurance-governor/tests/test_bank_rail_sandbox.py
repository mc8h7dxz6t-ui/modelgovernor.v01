"""FedNow / clearinghouse sandbox rail smoke tests."""
from __future__ import annotations

import json
import os
from decimal import Decimal
from unittest import mock

import httpx
import pytest

from platforms.common.integrations.bank_rail import dispatch_payment
from platforms.common.persistence.payment_types import PaymentInstruction, PaymentStatus


def _instruction() -> PaymentInstruction:
    return PaymentInstruction(
        payment_id="pay_sandbox_1",
        claim_id="claim-sandbox",
        idempotency_key="sandbox-idem-1",
        amount=Decimal("1.00"),
        currency="USD",
        payee_id="sandbox-beneficiary",
        status=PaymentStatus.PENDING,
    )


def test_fednow_sandbox_dispatch_with_mock_server():
    with mock.patch.dict(
        os.environ,
        {
            "PAYMENT_RAIL_MODE": "fednow_sandbox",
            "FEDNOW_SANDBOX_URL": "https://sandbox.fednow.example/v1/payments",
            "BANK_RAIL_API_TOKEN": "test-token-sandbox",
        },
        clear=False,
    ):
        mock_response = mock.Mock()
        mock_response.json.return_value = {"transactionId": "fednow-tx-999", "status": "COMPLETED"}
        mock_response.raise_for_status = mock.Mock()
        with mock.patch("platforms.common.integrations.bank_rail.httpx.Client") as client_cls:
            client_cls.return_value.__enter__.return_value.post.return_value = mock_response
            result = dispatch_payment(_instruction())

    assert result.rail == "fednow_sandbox"
    assert result.external_ref == "fednow-tx-999"
    assert result.status == PaymentStatus.COMPLETED


def test_clearinghouse_sandbox_requires_url():
    with mock.patch.dict(os.environ, {"PAYMENT_RAIL_MODE": "clearinghouse_sandbox"}, clear=False):
        os.environ.pop("CLEARINGHOUSE_SANDBOX_URL", None)
        os.environ.pop("CLEARINGHOUSE_API_URL", None)
        with pytest.raises(RuntimeError, match="CLEARINGHOUSE"):
            dispatch_payment(_instruction())
