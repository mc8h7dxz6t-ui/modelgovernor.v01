from typing import Optional

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str


class ReserveRequest(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=255)
    trace_id: str = Field(..., min_length=1, max_length=255)
    idempotency_key: str = Field(..., min_length=1, max_length=255)
    model: str = Field(..., min_length=1, max_length=255)
    estimated_cost: float = Field(..., ge=0)


class ReserveResponse(BaseModel):
    idempotency_key: str
    status: str
    reserved_amount: float
    expires_in_seconds: int


class SettleRequest(BaseModel):
    idempotency_key: str = Field(..., min_length=1, max_length=255)
    actual_cost: float = Field(..., ge=0)
    provider_request_id: Optional[str] = Field(default=None, max_length=255)


class SettleResponse(BaseModel):
    idempotency_key: str
    status: str
    actual_amount: float
