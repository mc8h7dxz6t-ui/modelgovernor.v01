from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str


class ReserveRequest(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=255)
    trace_id: str = Field(..., min_length=1, max_length=255)
    idempotency_key: str = Field(..., min_length=1, max_length=255)
    model: str = Field(..., min_length=1, max_length=255)
    estimated_cost: Decimal = Field(..., ge=0)
    trace_cap: Optional[Decimal] = Field(default=None, gt=0)


class ReserveResponse(BaseModel):
    idempotency_key: str
    status: str
    reserved_amount: Decimal
    expires_in_seconds: int


class SettleRequest(BaseModel):
    idempotency_key: Optional[str] = Field(default=None, min_length=1, max_length=255)
    outcome: Literal["IN_FLIGHT", "PROVIDER_TIMEOUT", "SETTLED"] = "SETTLED"
    actual_cost: Decimal = Field(default=Decimal("0"), ge=0)
    dispatch_attempt_key: Optional[str] = Field(default=None, min_length=1, max_length=255)
    provider_name: Optional[str] = Field(default=None, max_length=255)
    model: Optional[str] = Field(default=None, max_length=255)
    provider_request_id: Optional[str] = Field(default=None, max_length=255)
    reason: Optional[str] = Field(default=None, max_length=255)


class SettleResponse(BaseModel):
    idempotency_key: str
    status: str
    actual_amount: Decimal
