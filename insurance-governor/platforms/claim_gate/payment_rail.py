"""Payment rail stub — idempotent payout instruction with audit trail."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum


class PaymentStatus(str, Enum):
    PENDING = "PENDING"
    SUBMITTED = "SUBMITTED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"


@dataclass
class PaymentInstruction:
    payment_id: str
    claim_id: str
    idempotency_key: str
    amount: Decimal
    currency: str
    payee_id: str
    status: PaymentStatus
    rail: str = "ach_stub"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    reference: str | None = None


# In-memory idempotency store for stub/demo (production → Postgres)
_IDEMPOTENCY: dict[str, PaymentInstruction] = {}


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
    if idempotency_key in _IDEMPOTENCY:
        return _IDEMPOTENCY[idempotency_key]

    if gate_decision != "APPROVED":
        instr = PaymentInstruction(
            payment_id=f"pay_{uuid.uuid4().hex[:12]}",
            claim_id=claim_id,
            idempotency_key=idempotency_key,
            amount=amount,
            currency=currency,
            payee_id=payee_id,
            status=PaymentStatus.BLOCKED,
            reference=f"blocked:{gate_decision}",
        )
        _IDEMPOTENCY[idempotency_key] = instr
        return instr

    if not crystal_id:
        instr = PaymentInstruction(
            payment_id=f"pay_{uuid.uuid4().hex[:12]}",
            claim_id=claim_id,
            idempotency_key=idempotency_key,
            amount=amount,
            currency=currency,
            payee_id=payee_id,
            status=PaymentStatus.BLOCKED,
            reference="no_governance_crystal",
        )
        _IDEMPOTENCY[idempotency_key] = instr
        return instr

    instr = PaymentInstruction(
        payment_id=f"pay_{uuid.uuid4().hex[:12]}",
        claim_id=claim_id,
        idempotency_key=idempotency_key,
        amount=amount,
        currency=currency,
        payee_id=payee_id,
        status=PaymentStatus.COMPLETED,
        reference=f"crystal:{crystal_id}",
    )
    _IDEMPOTENCY[idempotency_key] = instr
    return instr


def reset_payment_store() -> None:
    _IDEMPOTENCY.clear()
