"""Tamper-evident privileged admin action logging."""
from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from .security_seal import GENESIS_HASH, compute_row_hash

if TYPE_CHECKING:
    from .auth_oidc import AuthContext

logger = logging.getLogger(__name__)


def schema_supports_admin_audit(session: Session) -> bool:
    dialect = session.bind.dialect.name
    if dialect == "postgresql":
        row = session.execute(
            text(
                """
                SELECT 1 FROM information_schema.tables
                WHERE table_name = 'admin_audit_log'
                """
            )
        ).first()
        return row is not None
    if dialect == "sqlite":
        row = session.execute(
            text(
                """
                SELECT 1 FROM sqlite_master
                WHERE type = 'table' AND name = 'admin_audit_log'
                """
            )
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
    meta_sql = ":meta" if session.bind.dialect.name == "sqlite" else ":meta::jsonb"
    row = session.execute(
        text(
            f"""
            INSERT INTO admin_audit_log (
                actor_subject, actor_method, actor_roles, action, resource, details
            )
            VALUES (
                :actor_subject, :actor_method, :actor_roles, :action, :resource, {meta_sql}
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
            "meta": json.dumps(payload_details),
        },
    ).mappings().first()
    if row is None:
        return None

    audit_id = int(row["audit_id"])
    recorded_at = str(row["recorded_at"])
    prev_hash = session.execute(
        text(
            """
            SELECT row_hash FROM admin_audit_log
            WHERE row_hash IS NOT NULL
            ORDER BY audit_id DESC LIMIT 1
            """
        )
    ).scalar_one_or_none() or GENESIS_HASH
    row_hash = compute_row_hash(
        event_id=audit_id,
        operation_id=resource,
        crystal_id=None,
        account_id=ctx.subject,
        event_type=action,
        exposure_delta="0.000000000000",
        metadata={"actor_roles": actor_roles, **payload_details},
        prev_hash=prev_hash,
        recorded_at=recorded_at,
    )
    session.execute(
        text(
            """
            UPDATE admin_audit_log
            SET prev_hash = :prev_hash, row_hash = :row_hash
            WHERE audit_id = :audit_id
            """
        ),
        {"prev_hash": prev_hash, "row_hash": row_hash, "audit_id": audit_id},
    )
    logger.info("admin audit action=%s resource=%s actor=%s", action, resource, ctx.subject)
    return audit_id
