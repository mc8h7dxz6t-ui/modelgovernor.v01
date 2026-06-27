"""Read-only governance evaluation for shadow/enforce intercept gates.

Evaluators return bool only — no ledger writes. Business operations run after the gate
so SHADOW passthrough never masks InsufficientFunds or similar ledger errors.
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

from .schemas import ReserveRequest, SettleRequest

try:
    from . import attribution
except ImportError:  # pragma: no cover
    attribution = None  # type: ignore[assignment]


def _model_policy_enabled(session: Session, model: str) -> bool:
    row = session.execute(
        text(
            """
            SELECT enabled
            FROM model_policy_registry
            WHERE model_name = :model_name
            """
        ),
        {"model_name": model},
    ).mappings().first()
    return bool(row and row["enabled"])


def evaluate_reserve_governance(
    session: Session,
    request: ReserveRequest,
    *,
    auth_tenant_id: str,
) -> bool:
    if not _model_policy_enabled(session, request.model):
        return False

    if attribution and attribution.schema_supports_attribution(session):
        identity = attribution.identity_from_reserve(request)
        if identity["tenant_id"] != auth_tenant_id:
            return False

    return True


def evaluate_settle_governance(
    session: Session,
    request: SettleRequest,
    *,
    auth_tenant_id: str,
) -> bool:
    row = session.execute(
        text(
            """
            SELECT model, tenant_id
            FROM escrow_ledger
            WHERE idempotency_key = :idempotency_key
            """
        ),
        {"idempotency_key": request.idempotency_key},
    ).mappings().first()
    if not row:
        return True

    if not _model_policy_enabled(session, str(row["model"])):
        return False

    if attribution and attribution.schema_supports_attribution(session):
        stored_tenant = row.get("tenant_id") or "default-tenant"
        if stored_tenant != auth_tenant_id:
            return False
        if request.tenant_id and request.tenant_id != stored_tenant:
            return False

    return True
