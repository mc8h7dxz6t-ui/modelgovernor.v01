"""Payment rail types — shared between rail and persistence."""
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
    crystal_id: str | None = None
    external_ref: str | None = None

    @staticmethod
    def new_id() -> str:
        return f"pay_{uuid.uuid4().hex[:12]}"
