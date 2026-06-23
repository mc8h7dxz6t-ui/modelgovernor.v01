from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, Literal, Optional

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


class AuditLogEntry(BaseModel):
    log_id: int
    admin_user_id: str
    action_type: str
    subject_key: str
    wallet_id: Optional[str]
    operation_id: Optional[str]
    details: Dict[str, object]
    applied_at: datetime


class AuditLogResponse(BaseModel):
    items: list[AuditLogEntry]
    total: int
    limit: int
    offset: int


class SpendReportItem(BaseModel):
    wallet_id: str
    model: str
    operations: int
    total_cost: Decimal
    input_tokens: int = 0
    output_tokens: int = 0


class SpendReportResponse(BaseModel):
    generated_at: datetime
    from_timestamp: Optional[datetime]
    to_timestamp: Optional[datetime]
    items: list[SpendReportItem]


class WalletSummaryResponse(BaseModel):
    wallet_id: str
    balance: Decimal
    reserved_total: Decimal
    locked: bool
    lock_reason: Optional[str]
    locked_at: Optional[datetime]
    last_event_type: Optional[str]
    last_event_at: Optional[datetime]


class SourceDocument(BaseModel):
    document_id: str = Field(..., min_length=1, max_length=255)
    source_uri: str = Field(..., min_length=1, max_length=1024)
    content: str = Field(..., min_length=1, max_length=20000)


class ComputationTask(BaseModel):
    task_id: str = Field(..., min_length=1, max_length=255)
    expression: str = Field(..., min_length=1, max_length=1024)
    variables: Dict[str, Decimal] = Field(default_factory=dict)
    expected_unit: Optional[str] = Field(default=None, max_length=64)


class WorkflowCitation(BaseModel):
    source_uri: str
    document_id: str
    quote: str = Field(..., min_length=1, max_length=1024)


class WorkflowComputationResult(BaseModel):
    task_id: str
    value: Decimal
    expected_unit: Optional[str]


class AgentDecision(BaseModel):
    agent: Literal["ingest", "retrieve", "compute", "report", "critic"]
    status: Literal["OK", "REJECTED", "SKIPPED"]
    reason: str
    latency_ms: int = Field(..., ge=0)
    routing_tier: Literal["fast-8b", "reasoning-large"] = "fast-8b"


class OrchestrationWorkflowRequest(BaseModel):
    workflow_id: str = Field(..., min_length=1, max_length=255)
    user_id: str = Field(..., min_length=1, max_length=255)
    query: str = Field(..., min_length=1, max_length=4000)
    runtime_mode: Optional[Literal["coexisting", "standalone"]] = None
    external_context_id: Optional[str] = Field(default=None, max_length=255)
    regulated: bool = False
    max_cost: Decimal = Field(default=Decimal("2.500000"), gt=0)
    max_latency_ms: int = Field(default=4000, ge=100, le=120000)
    documents: list[SourceDocument] = Field(default_factory=list)
    computations: list[ComputationTask] = Field(default_factory=list)


class OrchestrationWorkflowResponse(BaseModel):
    run_id: str
    workflow_id: str
    runtime_mode: Literal["coexisting", "standalone"]
    state: Literal["PUBLISHED", "REJECTED"]
    cache_hit: bool
    routing_tier: Literal["fast-8b", "reasoning-large"]
    estimated_cost: Decimal
    citations: list[WorkflowCitation]
    computations: list[WorkflowComputationResult]
    report_payload: Dict[str, Any]
    critic_passed: bool
    critic_issues: list[str]
    agent_decisions: list[AgentDecision]
