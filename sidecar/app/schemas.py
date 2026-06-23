from datetime import datetime
from decimal import Decimal
from typing import Dict, Literal, Optional

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


# ---------------------------------------------------------------------------
# Phase 3: Reconciliation and admin correction schemas
# ---------------------------------------------------------------------------


class ReconciliationSummary(BaseModel):
    """Point-in-time snapshot of ledger health for the operations dashboard."""

    generated_at: datetime
    total_operations: int
    by_status: Dict[str, int]
    stranded_count: int
    stranded_reserved_total: Decimal
    locked_wallets_count: int
    drift_enforced_total: int
    drift_tolerated_total: int
    anomaly_flag: bool


class StrandedOperationSummary(BaseModel):
    """Summary of a single STRANDED operation awaiting admin review."""

    idempotency_key: str
    user_id: str
    trace_id: str
    model: str
    reserved_amount: Decimal
    created_at: datetime
    expired_at: Optional[datetime]
    dispatch_started_at: Optional[datetime]
    terminal_reason: Optional[str]


class AdminCorrectionRequest(BaseModel):
    """Request to administratively settle a STRANDED or EXPIRED operation."""

    idempotency_key: str = Field(..., min_length=1, max_length=255)
    actual_amount: Decimal = Field(..., ge=0, description="Authoritative provider cost to settle at.")
    admin_user_id: str = Field(..., min_length=1, max_length=255, description="Identity of the admin performing this correction.")
    admin_reason: str = Field(..., min_length=1, max_length=1024, description="Mandatory reason for audit trail.")
    dispatch_attempt_key: Optional[str] = Field(default=None, max_length=255)
    provider_name: Optional[str] = Field(default=None, max_length=255)


class AdminCorrectionResponse(BaseModel):
    idempotency_key: str
    previous_status: str
    status: str
    actual_amount: Decimal
    correction_applied: bool


class WalletUnlockRequest(BaseModel):
    """Request to unlock a wallet that was locked due to drift enforcement."""

    user_id: str = Field(..., min_length=1, max_length=255)
    admin_user_id: str = Field(..., min_length=1, max_length=255)
    admin_reason: str = Field(..., min_length=1, max_length=1024)


class WalletUnlockResponse(BaseModel):
    user_id: str
    unlocked: bool
    message: str
