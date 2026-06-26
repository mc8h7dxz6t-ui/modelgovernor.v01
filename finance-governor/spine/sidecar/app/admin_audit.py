"""Privileged admin action audit trail."""
from __future__ import annotations

import hashlib
import json
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

GENESIS_HASH = "0" * 64


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
    actor_subject: str,
    actor_method: str,
    action: str,
    target: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> int | None:
    if not schema_supports_admin_audit(session):
        return None

    meta = metadata or {}
    meta_sql = ":meta" if session.bind.dialect.name == "sqlite" else ":meta::jsonb"
    prev_hash = (
        session.execute(
            text("SELECT row_hash FROM admin_audit_log WHERE row_hash IS NOT NULL ORDER BY audit_id DESC LIMIT 1")
        ).scalar_one_or_none()
        or GENESIS_HASH
    )
    audit_id = session.execute(
        text(
            f"""
            INSERT INTO admin_audit_log (
                actor_subject, actor_method, action, target, metadata, prev_hash, row_hash
            ) VALUES (
                :actor, :method, :action, :target, {meta_sql}, :prev, :placeholder
            )
            RETURNING audit_id
            """
        ),
        {
            "actor": actor_subject,
            "method": actor_method,
            "action": action,
            "target": target,
            "meta": json.dumps(meta, sort_keys=True),
            "prev": prev_hash,
            "placeholder": prev_hash,
        },
    ).scalar_one()

    recorded_at = session.execute(
        text("SELECT recorded_at FROM admin_audit_log WHERE audit_id = :id"),
        {"id": audit_id},
    ).scalar_one()
    row_hash = hashlib.sha256(
        json.dumps(
            {
                "audit_id": int(audit_id),
                "actor_subject": actor_subject,
                "actor_method": actor_method,
                "action": action,
                "target": target,
                "metadata": meta,
                "prev_hash": prev_hash,
                "recorded_at": str(recorded_at),
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()
    session.execute(
        text("UPDATE admin_audit_log SET row_hash = :rh WHERE audit_id = :id"),
        {"rh": row_hash, "id": audit_id},
    )
    return int(audit_id)
