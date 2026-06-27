"""Credit decision request schema."""
from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, Field, field_validator


class CreditRequest(BaseModel):
    application_id: str
    exposure_amount: str
    model_version_id: str
    desk_id: str = "desk-default"
    feature_snapshot_hash: str = ""
    jurisdiction: str = "US"

    @field_validator("exposure_amount")
    @classmethod
    def decimal_amount(cls, v: str) -> str:
        try:
            Decimal(v)
        except Exception as exc:
            raise ValueError("invalid decimal amount") from exc
        return v
