"""AI cost attribution and agent accountability controls."""
from __future__ import annotations

import json
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from .config import Settings
from .metrics import get_counters
from .schemas import ReserveRequest, SettleRequest

MONEY_QUANTUM = Decimal("0.000001")

_DEFAULT_IDENTITY = {
    "tenant_id": "default-tenant",
    "session_id": "default-session",
    "agent_run_id": "default-agent-run",
    "workflow_step": "default-workflow-step",
}


class AttributionPolicyError(Exception):
    pass


class BudgetScopeExceededError(Exception):
    pass


def identity_from_reserve(request: ReserveRequest) -> dict[str, str]:
    return {
        "tenant_id": request.tenant_id or _DEFAULT_IDENTITY["tenant_id"],
        "session_id": request.session_id or _DEFAULT_IDENTITY["session_id"],
        "agent_run_id": request.agent_run_id or _DEFAULT_IDENTITY["agent_run_id"],
        "workflow_step": request.workflow_step or _DEFAULT_IDENTITY["workflow_step"],
    }


def identity_from_operation(operation: dict) -> dict[str, str]:
    return {
        "tenant_id": operation.get("tenant_id") or _DEFAULT_IDENTITY["tenant_id"],
        "session_id": operation.get("session_id") or _DEFAULT_IDENTITY["session_id"],
        "agent_run_id": operation.get("agent_run_id") or _DEFAULT_IDENTITY["agent_run_id"],
        "workflow_step": operation.get("workflow_step") or _DEFAULT_IDENTITY["workflow_step"],
    }


def validate_settlement_identity(operation: dict, request: SettleRequest) -> None:
    checks = (
        ("tenant_id", request.tenant_id, operation.get("tenant_id")),
        ("session_id", request.session_id, operation.get("session_id")),
        ("agent_run_id", request.agent_run_id, operation.get("agent_run_id")),
        ("workflow_step", request.workflow_step, operation.get("workflow_step")),
    )
    for field, incoming, stored in checks:
        if incoming and stored and incoming != stored:
            get_counters().increment("attribution_identity_mismatch_total")
            raise AttributionPolicyError(f"{field} does not match reserved operation identity")


def enforce_manual_approval(
    session: Session,
    settings: Settings,
    request: ReserveRequest,
    identity: dict[str, str],
    now: datetime,
) -> None:
    needs_approval = request.requires_manual_approval or _money(request.estimated_cost) > _money(
        settings.manual_approval_cost_threshold
    )
    if not needs_approval:
        return
    if request.manual_approval_id:
        return
    append_guardrail_incident(
        session,
        incident_type="APPROVAL_REQUIRED",
        idempotency_key=request.idempotency_key,
        user_id=request.user_id,
        identity=identity,
        details={
            "reason": "manual_approval_missing" if request.requires_manual_approval else "cost_threshold_exceeded",
            "estimated_cost": str(_money(request.estimated_cost)),
            "high_cost_tool": request.high_cost_tool,
        },
        now=now,
    )
    get_counters().increment("guardrail_approval_required_total")
    session.commit()
    raise AttributionPolicyError("manual approval is required for this operation")


def apply_reserve_budget_scopes(
    session: Session,
    settings: Settings,
    request: ReserveRequest,
    identity: dict[str, str],
    reserved_amount: Decimal,
    now: datetime,
) -> None:
    caps = budget_caps(request, settings)
    for scope_type, scope_key, cap_amount in (
        ("run", identity["agent_run_id"], caps["run"]),
        ("session", identity["session_id"], caps["session"]),
        ("user", request.user_id, caps["user"]),
        ("tenant", identity["tenant_id"], caps["tenant"]),
    ):
        apply_budget_delta(
            session,
            scope_type=scope_type,
            scope_key=scope_key,
            cap_amount=cap_amount,
            delta_amount=reserved_amount,
            now=now,
        )


def apply_settlement_budget_scopes(
    session: Session,
    settings: Settings,
    operation: dict,
    budget_delta: Decimal,
    now: datetime,
) -> None:
    if budget_delta == Decimal("0"):
        return
    caps = budget_caps_from_operation(operation, settings)
    for scope_type, scope_key, cap_amount in (
        ("run", operation["agent_run_id"], caps["run"]),
        ("session", operation["session_id"], caps["session"]),
        ("user", operation["user_id"], caps["user"]),
        ("tenant", operation["tenant_id"], caps["tenant"]),
    ):
        apply_budget_delta(
            session,
            scope_type=scope_type,
            scope_key=scope_key,
            cap_amount=cap_amount,
            delta_amount=budget_delta,
            now=now,
        )


def enforce_loop_guardrail(
    session: Session,
    operation: dict,
    request: SettleRequest,
    settings: Settings,
    now: datetime,
) -> None:
    signature = request.loop_signature
    if not signature:
        return
    scope_key = f"{operation['agent_run_id']}:{operation['workflow_step']}:{signature}"
    row = session.execute(
        text(
            """
            SELECT consecutive_count
            FROM execution_loop_state
            WHERE scope_key = :scope_key
            """
        ),
        {"scope_key": scope_key},
    ).mappings().first()
    if row and int(row["consecutive_count"]) >= settings.max_loop_repeats:
        identity = identity_from_operation(operation)
        append_guardrail_incident(
            session,
            incident_type="AGENT_LOOP_DETECTED",
            idempotency_key=operation["idempotency_key"],
            user_id=operation["user_id"],
            identity=identity,
            details={"loop_signature": signature, "consecutive_count": int(row["consecutive_count"])},
            now=now,
        )
        get_counters().increment("agent_loop_detected_total")
        session.commit()
        raise AttributionPolicyError("agent loop guardrail triggered")
    if row:
        session.execute(
            text(
                """
                UPDATE execution_loop_state
                SET consecutive_count = consecutive_count + 1, updated_at = :updated_at
                WHERE scope_key = :scope_key
                """
            ),
            {"scope_key": scope_key, "updated_at": now},
        )
    else:
        session.execute(
            text(
                """
                INSERT INTO execution_loop_state (scope_key, last_signature, consecutive_count, updated_at)
                VALUES (:scope_key, :signature, 1, :updated_at)
                """
            ),
            {"scope_key": scope_key, "signature": signature, "updated_at": now},
        )


def append_guardrail_incident(
    session: Session,
    *,
    incident_type: str,
    idempotency_key: str | None,
    user_id: str | None,
    identity: dict[str, str],
    details: dict[str, Any],
    now: datetime,
) -> None:
    details_json = json.dumps(details, sort_keys=True)
    if session.bind.dialect.name == "postgresql":
        session.execute(
            text(
                """
                INSERT INTO guardrail_incidents (
                    idempotency_key, user_id, tenant_id, session_id, agent_run_id,
                    workflow_step, incident_type, details, recorded_at
                ) VALUES (
                    :idempotency_key, :user_id, :tenant_id, :session_id, :agent_run_id,
                    :workflow_step, :incident_type, CAST(:details AS JSONB), :recorded_at
                )
                """
            ),
            {
                "idempotency_key": idempotency_key,
                "user_id": user_id,
                "tenant_id": identity["tenant_id"],
                "session_id": identity["session_id"],
                "agent_run_id": identity["agent_run_id"],
                "workflow_step": identity["workflow_step"],
                "incident_type": incident_type,
                "details": details_json,
                "recorded_at": now,
            },
        )
    else:
        session.execute(
            text(
                """
                INSERT INTO guardrail_incidents (
                    idempotency_key, user_id, tenant_id, session_id, agent_run_id,
                    workflow_step, incident_type, details, recorded_at
                ) VALUES (
                    :idempotency_key, :user_id, :tenant_id, :session_id, :agent_run_id,
                    :workflow_step, :incident_type, :details, :recorded_at
                )
                """
            ),
            {
                "idempotency_key": idempotency_key,
                "user_id": user_id,
                "tenant_id": identity["tenant_id"],
                "session_id": identity["session_id"],
                "agent_run_id": identity["agent_run_id"],
                "workflow_step": identity["workflow_step"],
                "incident_type": incident_type,
                "details": details_json,
                "recorded_at": now,
            },
        )


def record_lineage(
    session: Session,
    *,
    idempotency_key: str,
    identity: dict[str, str],
    user_id: str,
    event_type: str,
    request: ReserveRequest | SettleRequest,
    provider_request_id: str | None,
    state_snapshot: dict[str, Any],
    now: datetime,
) -> None:
    snapshot_json = json.dumps(state_snapshot, sort_keys=True)
    tool_input = getattr(request, "tool_input", None)
    params = {
        "idempotency_key": idempotency_key,
        "tenant_id": identity["tenant_id"],
        "user_id": user_id,
        "session_id": identity["session_id"],
        "agent_run_id": identity["agent_run_id"],
        "workflow_step": identity["workflow_step"],
        "event_type": event_type,
        "prompt_template_version": getattr(request, "prompt_template_version", None),
        "system_context_hash": getattr(request, "system_context_hash", None),
        "tool_name": getattr(request, "tool_name", None),
        "tool_input": tool_input,
        "raw_tool_output": getattr(request, "raw_tool_output", None),
        "provider_request_id": provider_request_id,
        "state_snapshot": snapshot_json,
        "recorded_at": now,
    }
    if session.bind.dialect.name == "postgresql":
        session.execute(
            text(
                """
                INSERT INTO execution_lineage (
                    idempotency_key, tenant_id, user_id, session_id, agent_run_id,
                    workflow_step, event_type, prompt_template_version, system_context_hash,
                    tool_name, tool_input, raw_tool_output, provider_request_id,
                    state_snapshot, recorded_at
                ) VALUES (
                    :idempotency_key, :tenant_id, :user_id, :session_id, :agent_run_id,
                    :workflow_step, :event_type, :prompt_template_version, :system_context_hash,
                    :tool_name, :tool_input, :raw_tool_output, :provider_request_id,
                    CAST(:state_snapshot AS JSONB), :recorded_at
                )
                """
            ),
            params,
        )
    else:
        session.execute(
            text(
                """
                INSERT INTO execution_lineage (
                    idempotency_key, tenant_id, user_id, session_id, agent_run_id,
                    workflow_step, event_type, prompt_template_version, system_context_hash,
                    tool_name, tool_input, raw_tool_output, provider_request_id,
                    state_snapshot, recorded_at
                ) VALUES (
                    :idempotency_key, :tenant_id, :user_id, :session_id, :agent_run_id,
                    :workflow_step, :event_type, :prompt_template_version, :system_context_hash,
                    :tool_name, :tool_input, :raw_tool_output, :provider_request_id,
                    :state_snapshot, :recorded_at
                )
                """
            ),
            params,
        )


def budget_caps(request: ReserveRequest, settings: Settings) -> dict[str, Decimal]:
    return {
        "run": _money(request.run_budget or settings.default_run_budget_amount),
        "session": _money(request.session_budget or settings.default_session_budget_amount),
        "user": _money(request.user_budget or settings.default_user_budget_amount),
        "tenant": _money(request.tenant_budget or settings.default_tenant_budget_amount),
    }


def budget_caps_from_operation(operation: dict, settings: Settings) -> dict[str, Decimal]:
    return {
        "run": _money(settings.default_run_budget_amount),
        "session": _money(settings.default_session_budget_amount),
        "user": _money(settings.default_user_budget_amount),
        "tenant": _money(settings.default_tenant_budget_amount),
    }


def apply_budget_delta(
    session: Session,
    *,
    scope_type: str,
    scope_key: str,
    cap_amount: Decimal,
    delta_amount: Decimal,
    now: datetime,
) -> None:
    session.execute(
        text(
            """
            INSERT INTO budget_scope_state (scope_type, scope_key, cap_amount, consumed_amount, updated_at)
            VALUES (:scope_type, :scope_key, :cap_amount, 0.000000, :updated_at)
            ON CONFLICT (scope_type, scope_key) DO NOTHING
            """
        ),
        {
            "scope_type": scope_type,
            "scope_key": scope_key,
            "cap_amount": cap_amount,
            "updated_at": now,
        },
    )
    row = session.execute(
        text(
            """
            UPDATE budget_scope_state
            SET consumed_amount = consumed_amount + :delta_amount,
                updated_at = :updated_at
            WHERE scope_type = :scope_type
              AND scope_key = :scope_key
              AND consumed_amount + :delta_amount <= cap_amount
            RETURNING scope_key
            """
        ),
        {
            "scope_type": scope_type,
            "scope_key": scope_key,
            "delta_amount": delta_amount,
            "updated_at": now,
        },
    ).mappings().first()
    if not row:
        get_counters().increment("budget_scope_exceeded_total")
        raise BudgetScopeExceededError(f"{scope_type} budget scope exceeded")


def schema_supports_attribution(session: Session) -> bool:
    if session.bind.dialect.name == "sqlite":
        rows = session.execute(text("PRAGMA table_info(escrow_ledger)")).fetchall()
        return any(row[1] == "tenant_id" for row in rows)
    found = session.execute(
        text(
            """
            SELECT 1
            FROM information_schema.columns
            WHERE table_name = 'escrow_ledger' AND column_name = 'tenant_id'
            """
        )
    ).first()
    return found is not None


def _money(value: Decimal | str | int | float | None) -> Decimal:
    return Decimal(value or 0).quantize(MONEY_QUANTUM)
