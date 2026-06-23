from decimal import Decimal
from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str
    details: dict[str, str | bool | None] | None = None


class ReserveRequest(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=255)
    trace_id: str = Field(..., min_length=1, max_length=255)
    idempotency_key: str = Field(..., min_length=1, max_length=255)
    model: str = Field(..., min_length=1, max_length=255)
    estimated_cost: Decimal = Field(..., ge=0)
    trace_cap: Optional[Decimal] = Field(default=None, gt=0)
    tenant_id: Optional[str] = Field(default=None, min_length=1, max_length=255)
    session_id: Optional[str] = Field(default=None, min_length=1, max_length=255)
    agent_run_id: Optional[str] = Field(default=None, min_length=1, max_length=255)
    workflow_step: Optional[str] = Field(default=None, min_length=1, max_length=255)
    policy_version: str = Field(default="v1", min_length=1, max_length=64)
    run_budget: Optional[Decimal] = Field(default=None, gt=0)
    session_budget: Optional[Decimal] = Field(default=None, gt=0)
    tenant_budget: Optional[Decimal] = Field(default=None, gt=0)
    user_budget: Optional[Decimal] = Field(default=None, gt=0)
    requires_manual_approval: bool = False
    manual_approval_id: Optional[str] = Field(default=None, min_length=1, max_length=255)
    high_cost_tool: Optional[str] = Field(default=None, min_length=1, max_length=255)


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
    tenant_id: Optional[str] = Field(default=None, min_length=1, max_length=255)
    user_id: Optional[str] = Field(default=None, min_length=1, max_length=255)
    session_id: Optional[str] = Field(default=None, min_length=1, max_length=255)
    agent_run_id: Optional[str] = Field(default=None, min_length=1, max_length=255)
    workflow_step: Optional[str] = Field(default=None, min_length=1, max_length=255)
    policy_version: str = Field(default="v1", min_length=1, max_length=64)
    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    cached_input_tokens: int = Field(default=0, ge=0)
    cached_output_tokens: int = Field(default=0, ge=0)
    latency_ms: int = Field(default=0, ge=0)
    retry_count: int = Field(default=0, ge=0)
    failover_count: int = Field(default=0, ge=0)
    loop_signature: Optional[str] = Field(default=None, min_length=1, max_length=255)
    prompt_template_version: Optional[str] = Field(default=None, min_length=1, max_length=255)
    system_context_hash: Optional[str] = Field(default=None, min_length=1, max_length=255)
    tool_name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    tool_input: Optional[str] = None
    raw_tool_output: Optional[str] = None
    state_snapshot: Optional[dict[str, Any]] = None


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
    attempts: list[DispatchAttemptResponse] = Field(default_factory=list)


class OperationsListResponse(BaseModel):
    operations: list[OperationStatusResponse]
    total: int


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


class DiagnosticStatusResponse(BaseModel):
    diagnostic_mode: bool
    diagnostic_component: Optional[str] = None
    diagnostic_reason: Optional[str] = None


class LedgerChainBreakResponse(BaseModel):
    event_id: int
    reason: str


class LedgerChainVerificationResponse(BaseModel):
    valid: bool
    sealed_count: int
    unsealed_count: int
    total_events: int
    head_hash: Optional[str] = None
    first_break: Optional[LedgerChainBreakResponse] = None


class LedgerAnchorResponse(BaseModel):
    anchored: bool
    anchor_id: Optional[int] = None
    head_hash: Optional[str] = None
    sealed_count: int = 0
    total_events: int = 0
    source: Optional[str] = None
    reason: Optional[str] = None
    s3_anchored: bool = False
    s3_key: Optional[str] = None


class AdminAuditEntryResponse(BaseModel):
    audit_id: int
    actor_subject: str
    actor_method: str
    actor_roles: Optional[str]
    action: str
    resource: str
    details: dict[str, Any]
    recorded_at: datetime


class AdminAuditLogResponse(BaseModel):
    entries: list[AdminAuditEntryResponse]
    total: int


class AttributionSummaryRow(BaseModel):
    group_key: str
    operations: int
    reserved_total: Decimal
    settled_total: Decimal
    input_tokens: int
    output_tokens: int
    cached_input_tokens: int
    cached_output_tokens: int


class AttributionSummaryResponse(BaseModel):
    dimension: str
    rows: list[AttributionSummaryRow]


class GuardrailIncidentResponse(BaseModel):
    incident_id: int
    idempotency_key: Optional[str]
    user_id: Optional[str]
    tenant_id: Optional[str]
    session_id: Optional[str]
    agent_run_id: Optional[str]
    workflow_step: Optional[str]
    incident_type: str
    details: dict[str, Any]
    recorded_at: datetime


class GuardrailIncidentsResponse(BaseModel):
    incidents: list[GuardrailIncidentResponse]


class ExecutionLineageRecordResponse(BaseModel):
    lineage_id: int
    idempotency_key: str
    tenant_id: str
    user_id: str
    session_id: str
    agent_run_id: str
    workflow_step: str
    event_type: str
    prompt_template_version: Optional[str]
    system_context_hash: Optional[str]
    tool_name: Optional[str]
    tool_input: Optional[str]
    raw_tool_output: Optional[str]
    provider_request_id: Optional[str]
    state_snapshot: dict[str, Any]
    recorded_at: datetime


class ExecutionLineageResponse(BaseModel):
    records: list[ExecutionLineageRecordResponse]
