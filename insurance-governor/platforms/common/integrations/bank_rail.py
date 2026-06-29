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
    if mode in ("fednow", "fednow_sandbox"):
        return _dispatch_fednow(instruction, sandbox=mode == "fednow_sandbox")
    if mode in ("clearinghouse", "ach", "clearinghouse_sandbox"):
        return _dispatch_clearinghouse(instruction, sandbox="sandbox" in mode)
    raise ValueError(f"unsupported PAYMENT_RAIL_MODE: {mode}")


def _auth_headers() -> dict[str, str]:
    headers = {"content-type": "application/json", "accept": "application/json"}
    token = os.environ.get("BANK_RAIL_API_TOKEN") or os.environ.get("FEDNOW_API_TOKEN")
    if token:
        headers["authorization"] = f"Bearer {token}"
    return headers


def _dispatch_fednow(instruction: PaymentInstruction, *, sandbox: bool = False) -> RailDispatchResult:
    url = os.environ.get("FEDNOW_SANDBOX_URL" if sandbox else "FEDNOW_API_URL")
    if not url and sandbox:
        url = os.environ.get("FEDNOW_API_URL")
    if not url:
        raise RuntimeError("FEDNOW_API_URL or FEDNOW_SANDBOX_URL required for fednow rail")
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
        rail="fednow_sandbox" if sandbox else "fednow",
        status=PaymentStatus.SUBMITTED if data.get("status") == "PENDING" else PaymentStatus.COMPLETED,
    )


def _dispatch_clearinghouse(instruction: PaymentInstruction, *, sandbox: bool = False) -> RailDispatchResult:
    url = os.environ.get("CLEARINGHOUSE_SANDBOX_URL" if sandbox else "CLEARINGHOUSE_API_URL") or os.environ.get("ACH_API_URL")
    if not url and sandbox:
        url = os.environ.get("CLEARINGHOUSE_API_URL")
    if not url:
        raise RuntimeError("CLEARINGHOUSE_API_URL required for clearinghouse rail")
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
        rail="clearinghouse_sandbox" if sandbox else "clearinghouse",
        status=PaymentStatus.COMPLETED,
    )
