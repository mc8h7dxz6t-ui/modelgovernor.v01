"""Guardrail incident recording for compliance review."""
from __future__ import annotations

import json
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


def schema_supports_guardrail_incidents(session: Session) -> bool:
    try:
        session.execute(text("SELECT 1 FROM guardrail_incidents LIMIT 1"))
        return True
    except Exception:
        return False


def record_guardrail_incident(
    session: Session,
    *,
    operation_id: str | None,
    crystal_id: str | None,
    incident_type: str,
    platform: str,
    metadata: dict[str, Any] | None = None,
) -> None:
    if not schema_supports_guardrail_incidents(session):
        return
    meta_json = json.dumps(metadata or {})
    meta_sql = ":metadata" if session.bind.dialect.name == "sqlite" else ":metadata::jsonb"
    session.execute(
        text(
            f"""
            INSERT INTO guardrail_incidents (
                operation_id, crystal_id, incident_type, platform, metadata
            ) VALUES (
                :operation_id, :crystal_id, :incident_type, :platform, {meta_sql}
            )
            """
        ),
        {
            "operation_id": operation_id,
            "crystal_id": crystal_id,
            "incident_type": incident_type,
            "platform": platform,
            "metadata": meta_json,
        },
    )


def list_recent_incidents(session: Session, *, limit: int = 50) -> list[dict]:
    if not schema_supports_guardrail_incidents(session):
        return []
    rows = session.execute(
        text(
            """
            SELECT incident_id, operation_id, crystal_id, incident_type, platform, metadata, recorded_at
            FROM guardrail_incidents
            ORDER BY incident_id DESC
            LIMIT :limit
            """
        ),
        {"limit": limit},
    ).mappings().all()
    out = []
    for row in rows:
        item = dict(row)
        meta = item.get("metadata")
        if isinstance(meta, str):
            item["metadata"] = json.loads(meta)
        out.append(item)
    return out
