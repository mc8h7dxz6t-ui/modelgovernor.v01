"""Tamper-evident privileged admin action logging."""
from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from .claim_seal import GENESIS_HASH, compute_row_hash

if TYPE_CHECKING:
    from .auth_oidc import AuthContext

logger = logging.getLogger(__name__)


def schema_supports_admin_audit(session: Session) -> bool:
    dialect = session.bind.dialect.name
    if dialect == "postgresql":
        row = session.execute(
            text("SELECT 1 FROM information_schema.tables WHERE table_name = 'admin_audit_log'")
        ).first()
        return row is not None
    if dialect == "sqlite":
        row = session.execute(
            text("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'admin_audit_log'")
        ).first()
        return row is not None
    return False


def record_admin_action(
    session: Session,
    *,
    ctx: AuthContext,
    action: str,
    resource: str,
    details: dict[str, Any] | None = None,
) -> int | None:
    if not schema_supports_admin_audit(session):
        return None

    payload_details = details or {}
    actor_roles = ",".join(sorted(ctx.roles))

    row = session.execute(
        text(
            """
            INSERT INTO admin_audit_log (
                actor_subject, actor_method, actor_roles, action, resource, details
            ) VALUES (
                :actor_subject, :actor_method, :actor_roles, :action, :resource, :details
            )
            RETURNING audit_id, recorded_at
            """
        ),
        {
            "actor_subject": ctx.subject,
            "actor_method": ctx.method,
            "actor_roles": actor_roles,
            "action": action,
            "resource": resource,
            "details": json.dumps(payload_details),
        },
    ).mappings().first()

    if row is None:
        return None

    audit_id = int(row["audit_id"])
    recorded_at = str(row["recorded_at"])
    _seal_admin_audit_row(
        session,
        audit_id=audit_id,
        actor_subject=ctx.subject,
        actor_method=ctx.method,
        actor_roles=actor_roles,
        action=action,
        resource=resource,
        details=payload_details,
        recorded_at=recorded_at,
    )
    session.commit()
    logger.info("admin audit action=%s resource=%s actor=%s", action, resource, ctx.subject)
    return audit_id


def _seal_admin_audit_row(
    session: Session,
    *,
    audit_id: int,
    actor_subject: str,
    actor_method: str,
    actor_roles: str,
    action: str,
    resource: str,
    details: dict[str, Any],
    recorded_at: str,
) -> None:
    prev_hash = session.execute(
        text(
            """
            SELECT row_hash FROM admin_audit_log
            WHERE row_hash IS NOT NULL ORDER BY audit_id DESC LIMIT 1
            """
        )
    ).scalar_one_or_none() or GENESIS_HASH

    row_hash = compute_row_hash(
        event_id=audit_id,
        operation_id=resource,
        crystal_id=None,
        account_id=actor_subject,
        event_type=action,
        reserve_delta="0",
        metadata={"actor_method": actor_method, "actor_roles": actor_roles, **details},
        prev_hash=prev_hash,
        recorded_at=recorded_at,
    )
    session.execute(
        text(
            """
            UPDATE admin_audit_log SET prev_hash = :prev_hash, row_hash = :row_hash
            WHERE audit_id = :audit_id
            """
        ),
        {"prev_hash": prev_hash, "row_hash": row_hash, "audit_id": audit_id},
    )
