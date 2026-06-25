"""Live banking rail adapters — FedNow, clearinghouse, with stub fallback."""
from __future__ import annotations

import os
from dataclasses import dataclass

import httpx

from platforms.common.persistence.payment_types import PaymentInstruction, PaymentStatus


@dataclass(frozen=True)
class RailDispatchResult:
    external_ref: str
    rail: str
    status: PaymentStatus


def payment_rail_mode() -> str:
    return os.environ.get("PAYMENT_RAIL_MODE", "stub").lower()


def dispatch_payment(instruction: PaymentInstruction) -> RailDispatchResult:
    mode = payment_rail_mode()
    if mode == "stub":
        return RailDispatchResult(
            external_ref=f"stub-{instruction.payment_id}",
            rail=instruction.rail,
            status=PaymentStatus.COMPLETED,
        )
    if mode == "fednow":
        return _dispatch_fednow(instruction)
    if mode in ("clearinghouse", "ach"):
        return _dispatch_clearinghouse(instruction)
    raise ValueError(f"unsupported PAYMENT_RAIL_MODE: {mode}")


def _auth_headers() -> dict[str, str]:
    headers = {"content-type": "application/json", "accept": "application/json"}
    token = os.environ.get("BANK_RAIL_API_TOKEN") or os.environ.get("FEDNOW_API_TOKEN")
    if token:
        headers["authorization"] = f"Bearer {token}"
    return headers


def _dispatch_fednow(instruction: PaymentInstruction) -> RailDispatchResult:
    url = os.environ.get("FEDNOW_API_URL")
    if not url:
        raise RuntimeError("FEDNOW_API_URL required when PAYMENT_RAIL_MODE=fednow")
    body = {
        "paymentId": instruction.payment_id,
        "amount": str(instruction.amount),
        "currency": instruction.currency,
        "creditorAccount": instruction.payee_id,
        "idempotencyKey": instruction.idempotency_key,
    }
    with httpx.Client(timeout=30.0) as client:
        response = client.post(url, json=body, headers=_auth_headers())
        response.raise_for_status()
        data = response.json()
    return RailDispatchResult(
        external_ref=str(data.get("transactionId", data.get("id", instruction.payment_id))),
        rail="fednow",
        status=PaymentStatus.SUBMITTED if data.get("status") == "PENDING" else PaymentStatus.COMPLETED,
    )


def _dispatch_clearinghouse(instruction: PaymentInstruction) -> RailDispatchResult:
    url = os.environ.get("CLEARINGHOUSE_API_URL") or os.environ.get("ACH_API_URL")
    if not url:
        raise RuntimeError("CLEARINGHOUSE_API_URL required when PAYMENT_RAIL_MODE=clearinghouse")
    body = {
        "payment_id": instruction.payment_id,
        "amount": str(instruction.amount),
        "currency": instruction.currency,
        "beneficiary": instruction.payee_id,
        "idempotency_key": instruction.idempotency_key,
    }
    with httpx.Client(timeout=30.0) as client:
        response = client.post(url, json=body, headers=_auth_headers())
        response.raise_for_status()
        data = response.json()
    return RailDispatchResult(
        external_ref=str(data.get("trace_id", data.get("confirmation", instruction.payment_id))),
        rail="clearinghouse",
        status=PaymentStatus.COMPLETED,
    )
