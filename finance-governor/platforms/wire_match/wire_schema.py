"""WireMatch — type-safe wire schema."""
from __future__ import annotations

from decimal import Decimal, InvalidOperation

from pydantic import BaseModel, field_validator


class WireRequest(BaseModel):
    wire_id: str
    beneficiary_name: str
    beneficiary_account: str
    reference: str
    amount: str
    currency: str = "USD"

    @field_validator("amount")
    @classmethod
    def decimal_amount(cls, v: str) -> str:
        try:
            d = Decimal(v)
        except InvalidOperation as exc:
            raise ValueError("amount must be decimal string") from exc
        if d <= 0:
            raise ValueError("amount must be positive")
        return str(d)
