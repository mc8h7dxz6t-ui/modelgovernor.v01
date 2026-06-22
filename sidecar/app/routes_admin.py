from __future__ import annotations

import json
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text

from .auth import require_internal_auth
from .db import get_db_session
from .schemas import (
    AuditEventResponse,
    DispatchAttemptResponse,
    OperationStatusResponse,
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
