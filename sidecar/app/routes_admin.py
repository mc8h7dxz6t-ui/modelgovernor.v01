from __future__ import annotations

import json
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text

from .auth import require_financial_admin, require_internal_auth
from .db import get_db_session
from .diagnostic_mode import clear_diagnostic_mode, diagnostic_snapshot
from .ledger_seal import verify_ledger_chain
from .metrics import get_counters
from .schemas import (
    AuditEventResponse,
    DiagnosticStatusResponse,
    DispatchAttemptResponse,
    LedgerChainVerificationResponse,
    OperationStatusResponse,
    OperationsListResponse,
    RecentAuditEventsResponse,
    TraceBudgetStatusResponse,
    WalletStatusResponse,
)

router = APIRouter(
    prefix="/internal",
    tags=["admin"],
    dependencies=[Depends(require_internal_auth)],
)


@router.get("/wallet/{user_id}", response_model=WalletStatusResponse)
def get_wallet_status(user_id: str) -> WalletStatusResponse:
    with get_db_session() as session:
        row = session.execute(
            text(
                """
                SELECT user_id, balance, active, lock_reason, locked_at, updated_at
                FROM user_wallets
                WHERE user_id = :user_id
                """
            ),
            {"user_id": user_id},
        ).mappings().first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="wallet not found")
    return WalletStatusResponse(**row)


@router.get("/operation/{idempotency_key}", response_model=OperationStatusResponse)
def get_operation_status(
    idempotency_key: str,
) -> OperationStatusResponse:
    with get_db_session() as session:
        row = session.execute(
            text(
                """
                SELECT
                    idempotency_key,
                    user_id,
                    trace_id,
                    model,
                    status,
                    reserved_amount,
                    actual_amount,
                    provider_request_id,
                    terminal_reason,
                    trace_cap_amount,
                    drift_amount,
                    created_at,
                    dispatch_started_at,
                    settled_at,
                    expired_at
                FROM escrow_ledger
                WHERE idempotency_key = :idempotency_key
                """
            ),
            {"idempotency_key": idempotency_key},
        ).mappings().first()
        attempts = session.execute(
            text(
                """
                SELECT
                    attempt_key,
                    provider_name,
                    model_name,
                    provider_request_id,
                    status,
                    terminal_reason,
                    created_at,
                    updated_at
                FROM provider_dispatch_attempts
                WHERE idempotency_key = :idempotency_key
                ORDER BY updated_at DESC, attempt_key DESC
                """
            ),
            {"idempotency_key": idempotency_key},
        ).mappings().all()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="operation not found")

    return OperationStatusResponse(
        **row,
        attempts=[DispatchAttemptResponse(**attempt) for attempt in attempts],
    )


@router.get("/operation/by-provider/{provider_request_id}", response_model=OperationStatusResponse)
def get_operation_by_provider_request_id(
    provider_request_id: str,
) -> OperationStatusResponse:
    with get_db_session() as session:
        row = session.execute(
            text(
                """
                SELECT idempotency_key
                FROM provider_dispatch_attempts
                WHERE provider_request_id = :provider_request_id
                """
            ),
            {"provider_request_id": provider_request_id},
        ).mappings().first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="provider request id not found")

    return get_operation_status(row["idempotency_key"])


@router.get("/operations", response_model=OperationsListResponse)
def list_operations(
    status: str | None = Query(default=None, description="Filter by escrow status e.g. STRANDED"),
    limit: int = Query(default=50, ge=1, le=200),
) -> OperationsListResponse:
    query = """
        SELECT idempotency_key
        FROM escrow_ledger
    """
    params: dict[str, Any] = {"limit": limit}
    if status:
        query += " WHERE status = :status"
        params["status"] = status
    query += " ORDER BY created_at DESC LIMIT :limit"

    with get_db_session() as session:
        rows = session.execute(text(query), params).mappings().all()

    operations = [get_operation_status(row["idempotency_key"]) for row in rows]
    return OperationsListResponse(operations=operations, total=len(operations))


@router.get("/trace/{trace_id}", response_model=TraceBudgetStatusResponse)
def get_trace_budget_status(
    trace_id: str,
) -> TraceBudgetStatusResponse:
    with get_db_session() as session:
        row = session.execute(
            text(
                """
                SELECT trace_id, cap_amount, reserved_total, settled_total, updated_at
                FROM trace_budget_state
                WHERE trace_id = :trace_id
                """
            ),
            {"trace_id": trace_id},
        ).mappings().first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="trace budget state not found")
    return TraceBudgetStatusResponse(**row)


@router.get("/events/recent", response_model=RecentAuditEventsResponse)
def get_recent_audit_events(
    limit: int = Query(default=25, ge=1, le=200),
) -> RecentAuditEventsResponse:
    with get_db_session() as session:
        rows = session.execute(
            text(
                """
                SELECT event_id, idempotency_key, user_id, event_type, amount_delta, metadata, recorded_at
                FROM ledger_events
                ORDER BY event_id DESC
                LIMIT :limit
                """
            ),
            {"limit": limit},
        ).mappings().all()
    events = [
        AuditEventResponse(
            event_id=row["event_id"],
            idempotency_key=row["idempotency_key"],
            user_id=row["user_id"],
            event_type=row["event_type"],
            amount_delta=Decimal(row["amount_delta"]),
            metadata=_parse_metadata(row["metadata"]),
            recorded_at=row["recorded_at"],
        )
        for row in rows
    ]
    return RecentAuditEventsResponse(events=events)


@router.get("/diagnostic/status", response_model=DiagnosticStatusResponse)
def get_diagnostic_status() -> DiagnosticStatusResponse:
    snap = diagnostic_snapshot()
    return DiagnosticStatusResponse(
        diagnostic_mode=bool(snap.get("diagnostic_mode")),
        diagnostic_component=snap.get("diagnostic_component"),
        diagnostic_reason=snap.get("diagnostic_reason"),
    )


@router.post(
    "/diagnostic/clear",
    response_model=DiagnosticStatusResponse,
    dependencies=[Depends(require_financial_admin)],
)
def post_clear_diagnostic_mode() -> DiagnosticStatusResponse:
    clear_diagnostic_mode()
    get_counters().increment("finance_audit_diagnostic_cleared_total")
    snap = diagnostic_snapshot()
    return DiagnosticStatusResponse(
        diagnostic_mode=bool(snap.get("diagnostic_mode")),
        diagnostic_component=snap.get("diagnostic_component"),
        diagnostic_reason=snap.get("diagnostic_reason"),
    )


@router.get("/ledger/verify-chain", response_model=LedgerChainVerificationResponse)
def get_ledger_verify_chain() -> LedgerChainVerificationResponse:
    with get_db_session() as session:
        result = verify_ledger_chain(session)

    if not result.valid:
        get_counters().increment("ledger_chain_verification_failed_total")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=result.to_dict(),
        )

    get_counters().increment("ledger_chain_verification_ok_total")
    return LedgerChainVerificationResponse(**result.to_dict())


def _parse_metadata(metadata: Any) -> dict[str, Any]:
    if metadata is None:
        return {}
    if isinstance(metadata, dict):
        return metadata
    if isinstance(metadata, str):
        try:
            parsed = json.loads(metadata)
        except json.JSONDecodeError:
            return {}
        if isinstance(parsed, dict):
            return parsed
    return {}
