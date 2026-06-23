from __future__ import annotations

import json
from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text

from .auth import require_internal_auth
from .db import get_db_session
from .schemas import (
    AttributionSummaryResponse,
    AttributionSummaryRow,
    ExecutionLineageRecordResponse,
    ExecutionLineageResponse,
    GuardrailIncidentResponse,
    GuardrailIncidentsResponse,
)

router = APIRouter(
    prefix="/internal",
    tags=["attribution"],
    dependencies=[Depends(require_internal_auth)],
)

_DIMENSION_COLUMNS = {
    "tenant": "tenant_id",
    "session": "session_id",
    "agent_run": "agent_run_id",
    "workflow_step": "workflow_step",
    "user": "user_id",
}


@router.get("/attribution/summary", response_model=AttributionSummaryResponse)
def get_attribution_summary(
    dimension: Literal["tenant", "session", "agent_run", "workflow_step", "user"] = Query(
        default="tenant"
    ),
    limit: int = Query(default=50, ge=1, le=500),
) -> AttributionSummaryResponse:
    column = _DIMENSION_COLUMNS[dimension]
    with get_db_session() as session:
        rows = session.execute(
            text(
                f"""
                SELECT
                    {column} AS group_key,
                    COUNT(*) AS operations,
                    COALESCE(SUM(reserved_amount), 0) AS reserved_total,
                    COALESCE(SUM(actual_amount), 0) AS settled_total,
                    COALESCE(SUM(input_tokens), 0) AS input_tokens,
                    COALESCE(SUM(output_tokens), 0) AS output_tokens,
                    COALESCE(SUM(cached_input_tokens), 0) AS cached_input_tokens,
                    COALESCE(SUM(cached_output_tokens), 0) AS cached_output_tokens
                FROM escrow_ledger
                GROUP BY {column}
                ORDER BY settled_total DESC
                LIMIT :limit
                """
            ),
            {"limit": limit},
        ).mappings().all()
    return AttributionSummaryResponse(
        dimension=dimension,
        rows=[
            AttributionSummaryRow(
                group_key=str(row["group_key"]),
                operations=int(row["operations"]),
                reserved_total=Decimal(str(row["reserved_total"])),
                settled_total=Decimal(str(row["settled_total"])),
                input_tokens=int(row["input_tokens"]),
                output_tokens=int(row["output_tokens"]),
                cached_input_tokens=int(row["cached_input_tokens"]),
                cached_output_tokens=int(row["cached_output_tokens"]),
            )
            for row in rows
        ],
    )


@router.get("/guardrail/incidents", response_model=GuardrailIncidentsResponse)
def get_guardrail_incidents(limit: int = Query(default=50, ge=1, le=500)) -> GuardrailIncidentsResponse:
    with get_db_session() as session:
        rows = session.execute(
            text(
                """
                SELECT incident_id, idempotency_key, user_id, tenant_id, session_id,
                       agent_run_id, workflow_step, incident_type, details, recorded_at
                FROM guardrail_incidents
                ORDER BY incident_id DESC
                LIMIT :limit
                """
            ),
            {"limit": limit},
        ).mappings().all()
    return GuardrailIncidentsResponse(
        incidents=[
            GuardrailIncidentResponse(
                incident_id=int(row["incident_id"]),
                idempotency_key=row["idempotency_key"],
                user_id=row["user_id"],
                tenant_id=row["tenant_id"],
                session_id=row["session_id"],
                agent_run_id=row["agent_run_id"],
                workflow_step=row["workflow_step"],
                incident_type=row["incident_type"],
                details=_parse_json(row["details"]),
                recorded_at=row["recorded_at"],
            )
            for row in rows
        ]
    )


@router.get("/lineage/{idempotency_key}", response_model=ExecutionLineageResponse)
def get_execution_lineage(idempotency_key: str) -> ExecutionLineageResponse:
    with get_db_session() as session:
        rows = session.execute(
            text(
                """
                SELECT lineage_id, idempotency_key, tenant_id, user_id, session_id,
                       agent_run_id, workflow_step, event_type, prompt_template_version,
                       system_context_hash, tool_name, tool_input, raw_tool_output,
                       provider_request_id, state_snapshot, recorded_at
                FROM execution_lineage
                WHERE idempotency_key = :idempotency_key
                ORDER BY lineage_id ASC
                """
            ),
            {"idempotency_key": idempotency_key},
        ).mappings().all()
    if not rows:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="lineage not found")
    return ExecutionLineageResponse(
        records=[
            ExecutionLineageRecordResponse(
                lineage_id=int(row["lineage_id"]),
                idempotency_key=row["idempotency_key"],
                tenant_id=row["tenant_id"],
                user_id=row["user_id"],
                session_id=row["session_id"],
                agent_run_id=row["agent_run_id"],
                workflow_step=row["workflow_step"],
                event_type=row["event_type"],
                prompt_template_version=row["prompt_template_version"],
                system_context_hash=row["system_context_hash"],
                tool_name=row["tool_name"],
                tool_input=row["tool_input"],
                raw_tool_output=row["raw_tool_output"],
                provider_request_id=row["provider_request_id"],
                state_snapshot=_parse_json(row["state_snapshot"]),
                recorded_at=row["recorded_at"],
            )
            for row in rows
        ]
    )


def _parse_json(value: object) -> dict:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}
