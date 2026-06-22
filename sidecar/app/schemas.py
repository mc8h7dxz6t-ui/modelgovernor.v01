from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str


class ReserveRequest(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=255)
    trace_id: str = Field(..., min_length=1, max_length=255)
    idempotency_key: str = Field(..., min_length=1, max_length=255)
    model: str = Field(..., min_length=1, max_length=255)
    estimated_cost: Decimal = Field(..., ge=0)


class ReserveResponse(BaseModel):
    idempotency_key: str
    status: str
    reserved_amount: Decimal
    expires_in_seconds: int


class SettleRequest(BaseModel):
    idempotency_key: str = Field(..., min_length=1, max_length=255)
    actual_cost: Decimal = Field(..., ge=0)
    provider_request_id: Optional[str] = Field(default=None, max_length=255)


class SettleResponse(BaseModel):
    idempotency_key: str
    status: str
    actual_amount: Decimal


class ProviderReconciliationRequest(BaseModel):
    reconciliation_key: str = Field(..., min_length=1, max_length=255)
    provider: str = Field(..., min_length=1, max_length=100)
    idempotency_key: Optional[str] = Field(default=None, min_length=1, max_length=255)
    provider_request_id: Optional[str] = Field(default=None, min_length=1, max_length=255)
    provider_actual_cost: Decimal = Field(..., ge=0)
    external_reference: Optional[str] = Field(default=None, max_length=255)


class ProviderReconciliationResponse(BaseModel):
    reconciliation_key: str
    idempotency_key: str
    status: str
    discrepancy_amount: Decimal
    reconciled: bool


class ProviderAdjustmentRequest(BaseModel):
    adjustment_key: str = Field(..., min_length=1, max_length=255)
    reconciliation_key: str = Field(..., min_length=1, max_length=255)
    reason: str = Field(..., min_length=1, max_length=255)


class ProviderAdjustmentResponse(BaseModel):
    adjustment_key: str
    reconciliation_key: str
    idempotency_key: str
    status: str
    corrected_actual_amount: Decimal
    wallet_delta: Decimal


class ReconciliationAnomalySummary(BaseModel):
    reconciliation_key: str
    idempotency_key: str
    provider: str
    discrepancy_amount: Decimal
    created_at: str


class ReconciliationSummaryResponse(BaseModel):
    matched_count: int
    mismatched_count: int
    resolved_count: int
    total_unresolved_discrepancy: Decimal
    anomalies: list[ReconciliationAnomalySummary]
