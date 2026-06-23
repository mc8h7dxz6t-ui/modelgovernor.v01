"""Admin reconciliation endpoints.

These routes provide operational visibility into the governance ledger and
enable authorised administrators to resolve anomalous states that cannot be
handled by the automated reconciler.

All routes require the standard internal authentication token and log every
mutating action to admin_audit_log and ledger_events for full auditability.

Endpoint summary
----------------
GET  /admin/reconciliation-summary   — point-in-time ledger health snapshot
GET  /admin/stranded-operations      — list STRANDED operations awaiting review
POST /admin/correct-operation        — force-settle a STRANDED or EXPIRED operation
POST /admin/unlock-wallet            — reactivate a wallet locked by drift enforcement
"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status

from .auth import require_internal_auth
from .config import get_settings
from .db import get_db_session
from .ledger import (
    NotFoundError,
    PolicyStateError,
    apply_admin_correction,
    get_reconciliation_summary,
    list_stranded_operations,
    unlock_wallet,
)
from .schemas import (
    AdminCorrectionRequest,
    AdminCorrectionResponse,
    ReconciliationSummary,
    StrandedOperationSummary,
    WalletUnlockRequest,
    WalletUnlockResponse,
)

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get(
    "/reconciliation-summary",
    response_model=ReconciliationSummary,
    dependencies=[Depends(require_internal_auth)],
    summary="Ledger health snapshot",
    description=(
        "Returns a point-in-time aggregate of ledger state: operation counts by "
        "status, total STRANDED exposure, locked wallet count, and drift event "
        "totals.  anomaly_flag is true whenever any material anomaly requires "
        "attention."
    ),
)
def reconciliation_summary() -> ReconciliationSummary:
    with get_db_session() as session:
        return get_reconciliation_summary(session)


@router.get(
    "/stranded-operations",
    response_model=List[StrandedOperationSummary],
    dependencies=[Depends(require_internal_auth)],
    summary="List STRANDED operations",
    description=(
        "Returns STRANDED operations ordered oldest-first.  STRANDED operations "
        "represent provider dispatches where the outcome is ambiguous and the "
        "reconciler preserved the hold pending explicit admin review.  Use "
        "POST /admin/correct-operation to resolve each entry."
    ),
)
def stranded_operations(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> List[StrandedOperationSummary]:
    with get_db_session() as session:
        return list_stranded_operations(session, limit=limit, offset=offset)


@router.post(
    "/correct-operation",
    response_model=AdminCorrectionResponse,
    dependencies=[Depends(require_internal_auth)],
    summary="Admin-correct a STRANDED or EXPIRED operation",
    description=(
        "Resolves a STRANDED or EXPIRED operation by applying the authoritative "
        "provider cost.  The correction follows the same settlement finalization "
        "path as normal settlement so that all balance mutations, trace-budget "
        "updates, and audit events are deterministic.  An ADMIN_CORRECTION_APPLIED "
        "event is appended to ledger_events and a row is written to admin_audit_log."
    ),
)
def correct_operation(request: AdminCorrectionRequest) -> AdminCorrectionResponse:
    try:
        with get_db_session() as session:
            return apply_admin_correction(session, get_settings(), request)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PolicyStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.post(
    "/unlock-wallet",
    response_model=WalletUnlockResponse,
    dependencies=[Depends(require_internal_auth)],
    summary="Unlock a wallet locked by drift enforcement",
    description=(
        "Reactivates a wallet that was locked when a settlement drift exceeded "
        "the configured tolerance.  The admin must supply a mandatory reason "
        "which is recorded in admin_audit_log.  If the wallet is already active "
        "the call succeeds with unlocked=false and no state is changed."
    ),
)
def unlock_wallet_endpoint(request: WalletUnlockRequest) -> WalletUnlockResponse:
    try:
        with get_db_session() as session:
            return unlock_wallet(
                session,
                user_id=request.user_id,
                admin_user_id=request.admin_user_id,
                admin_reason=request.admin_reason,
            )
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
