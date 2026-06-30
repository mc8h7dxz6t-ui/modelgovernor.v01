"""Payment rail — idempotent payout with Postgres persistence and live bank dispatch."""
from __future__ import annotations

from decimal import Decimal

from platforms.common.integrations.bank_rail import dispatch_payment, payment_rail_mode
from platforms.common.persistence.payment_store import get_payment_store, reset_payment_stores
from platforms.common.persistence.payment_types import PaymentInstruction, PaymentStatus

__all__ = ["PaymentInstruction", "PaymentStatus", "submit_payment", "reset_payment_store"]


def submit_payment(
    *,
    claim_id: str,
    amount: Decimal,
    currency: str,
    payee_id: str,
    idempotency_key: str,
    gate_decision: str,
    crystal_id: str | None = None,
) -> PaymentInstruction:
    store = get_payment_store()
    existing = store.get(idempotency_key)
    if existing is not None:
        return existing

    if gate_decision != "APPROVED":
        instr = PaymentInstruction(
            payment_id=PaymentInstruction.new_id(),
            claim_id=claim_id,
            idempotency_key=idempotency_key,
            amount=amount,
            currency=currency,
            payee_id=payee_id,
            status=PaymentStatus.BLOCKED,
            reference=f"blocked:{gate_decision}",
        )
        return store.save(instr)

    if not crystal_id:
        instr = PaymentInstruction(
            payment_id=PaymentInstruction.new_id(),
            claim_id=claim_id,
            idempotency_key=idempotency_key,
            amount=amount,
            currency=currency,
            payee_id=payee_id,
            status=PaymentStatus.BLOCKED,
            reference="no_governance_crystal",
        )
        return store.save(instr)

    instr = PaymentInstruction(
        payment_id=PaymentInstruction.new_id(),
        claim_id=claim_id,
        idempotency_key=idempotency_key,
        amount=amount,
        currency=currency,
        payee_id=payee_id,
        status=PaymentStatus.PENDING,
        crystal_id=crystal_id,
        reference=f"crystal:{crystal_id}",
        rail=payment_rail_mode() if payment_rail_mode() != "sandbox" else "ach_sandbox",
    )

    try:
        dispatch = dispatch_payment(instr)
        instr.status = dispatch.status
        instr.rail = dispatch.rail
        instr.external_ref = dispatch.external_ref
        instr.reference = f"external:{dispatch.external_ref}"
        if dispatch.status == PaymentStatus.COMPLETED:
            instr.status = PaymentStatus.COMPLETED
    except Exception as exc:  # noqa: BLE001 — surface rail failure without losing idempotency row
        instr.status = PaymentStatus.FAILED
        instr.reference = f"rail_error:{exc}"

    return store.save(instr)


def reset_payment_store() -> None:
    reset_payment_stores()
    get_payment_store().clear()
