"""Multi-rail attempt tracking for credit inference failover."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.orm import Session


def record_rail_attempt(
    session: Session,
    *,
    operation_id: str,
    platform: str,
    attempt_status: str,
    external_ref: str | None = None,
) -> str:
    attempt_key = f"{operation_id}:{uuid.uuid4().hex[:12]}"
    ts = datetime.now(timezone.utc)
    ts_param = ts.isoformat() if session.bind.dialect.name == "sqlite" else ts
    session.execute(
        text(
            """
            INSERT INTO platform_action_attempts (
                attempt_key, operation_id, platform, attempt_status, external_ref, created_at
            ) VALUES (
                :attempt_key, :operation_id, :platform, :attempt_status, :external_ref, :created_at
            )
            """
        ),
        {
            "attempt_key": attempt_key,
            "operation_id": operation_id,
            "platform": platform,
            "attempt_status": attempt_status,
            "external_ref": external_ref,
            "created_at": ts_param,
        },
    )
    return attempt_key


def list_attempts(session: Session, operation_id: str) -> list[dict]:
    rows = session.execute(
        text(
            """
            SELECT attempt_key, attempt_status, external_ref, created_at
            FROM platform_action_attempts
            WHERE operation_id = :operation_id
            ORDER BY created_at
            """
        ),
        {"operation_id": operation_id},
    ).mappings().all()
    return [dict(r) for r in rows]
