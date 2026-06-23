from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status

from .auth import require_internal_auth
from .db import get_db_session
from .ledger import (
    NotFoundError,
    get_spend_report,
    get_wallet_summary,
    list_admin_audit_log,
)
from .schemas import AuditLogResponse, SpendReportResponse, WalletSummaryResponse

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get(
    "/audit-log",
    response_model=AuditLogResponse,
    dependencies=[Depends(require_internal_auth)],
)
def audit_log(
    wallet_id: str | None = Query(default=None),
    operation_id: str | None = Query(default=None),
    event_type: str | None = Query(default=None),
    from_timestamp: datetime | None = Query(default=None),
    to_timestamp: datetime | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> AuditLogResponse:
    with get_db_session() as session:
        return list_admin_audit_log(
            session,
            wallet_id=wallet_id,
            operation_id=operation_id,
            action_type=event_type,
            from_timestamp=from_timestamp,
            to_timestamp=to_timestamp,
            limit=limit,
            offset=offset,
        )


@router.get(
    "/spend-report",
    response_model=SpendReportResponse,
    dependencies=[Depends(require_internal_auth)],
)
def spend_report(
    wallet_id: str | None = Query(default=None),
    model: str | None = Query(default=None),
    from_timestamp: datetime | None = Query(default=None),
    to_timestamp: datetime | None = Query(default=None),
) -> SpendReportResponse:
    with get_db_session() as session:
        return get_spend_report(
            session,
            wallet_id=wallet_id,
            model=model,
            from_timestamp=from_timestamp,
            to_timestamp=to_timestamp,
        )


@router.get(
    "/wallet-summary/{wallet_id}",
    response_model=WalletSummaryResponse,
    dependencies=[Depends(require_internal_auth)],
)
def wallet_summary(wallet_id: str) -> WalletSummaryResponse:
    try:
        with get_db_session() as session:
            return get_wallet_summary(session, wallet_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
