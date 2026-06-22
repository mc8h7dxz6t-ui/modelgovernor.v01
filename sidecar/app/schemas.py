from decimal import Decimal
from datetime import datetime
from typing import Any, Literal, Optional

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


class WalletStatusResponse(BaseModel):
    user_id: str
    balance: Decimal
    active: bool
    lock_reason: Optional[str]
    locked_at: Optional[datetime]
    updated_at: datetime


class DispatchAttemptResponse(BaseModel):
    model_config = {"protected_namespaces": ()}

    attempt_key: str
    provider_name: Optional[str]
    model_name: Optional[str]
    provider_request_id: Optional[str]
    status: str
    terminal_reason: Optional[str]
    created_at: datetime
    updated_at: datetime


class OperationStatusResponse(BaseModel):
    idempotency_key: str
    user_id: str
    trace_id: str
    model: str
    status: str
    reserved_amount: Decimal
    actual_amount: Decimal
    provider_request_id: Optional[str]
    terminal_reason: Optional[str]
    trace_cap_amount: Decimal
    drift_amount: Decimal
    created_at: datetime
    dispatch_started_at: Optional[datetime]
    settled_at: Optional[datetime]
    expired_at: Optional[datetime]
    attempts: list[DispatchAttemptResponse]


class TraceBudgetStatusResponse(BaseModel):
    trace_id: str
    cap_amount: Decimal
    reserved_total: Decimal
    settled_total: Decimal
    updated_at: datetime


class AuditEventResponse(BaseModel):
    event_id: int
    idempotency_key: str
    user_id: str
    event_type: str
    amount_delta: Decimal
    metadata: dict[str, Any]
    recorded_at: datetime


class RecentAuditEventsResponse(BaseModel):
    events: list[AuditEventResponse]
