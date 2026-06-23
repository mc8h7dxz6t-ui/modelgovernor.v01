from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .config import Settings
from .schemas import ReserveRequest, SettleRequest

MONEY_QUANTUM = Decimal("0.000001")


class LedgerError(Exception):
    pass


class ConflictError(LedgerError):
    pass


class InsufficientFundsError(LedgerError):
    pass


class NotFoundError(LedgerError):
    pass


class PolicyStateError(LedgerError):
    pass


class TraceCapExceededError(LedgerError):
    pass


@dataclass(frozen=True)
class OperationResult:
    idempotency_key: str
    status: str
    actual_amount: Decimal


def reserve_operation(session: Session, settings: Settings, request: ReserveRequest) -> OperationResult:
    identity = _identity_from_reserve(request)
    fingerprint = _fingerprint_reserve_request(request)
    existing = session.execute(
        text(
            """
            SELECT idempotency_key, status, actual_amount, request_fingerprint
            FROM escrow_ledger
            WHERE idempotency_key = :idempotency_key
            """
        ),
        {"idempotency_key": request.idempotency_key},
    ).mappings().first()
    if existing:
        if existing["request_fingerprint"] != fingerprint:
            raise ConflictError("idempotency key replay does not match original reserve request")
        return OperationResult(
            idempotency_key=existing["idempotency_key"],
            status=existing["status"],
            actual_amount=_money(existing["actual_amount"]),
        )

    now = _utcnow()
    if request.requires_manual_approval and not request.manual_approval_id:
        _append_guardrail_incident(
            session,
            incident_type="APPROVAL_REQUIRED",
            idempotency_key=request.idempotency_key,
            user_id=request.user_id,
            tenant_id=identity["tenant_id"],
            session_id=identity["session_id"],
            agent_run_id=identity["agent_run_id"],
            workflow_step=identity["workflow_step"],
            details={"reason": "manual_approval_missing", "high_cost_tool": request.high_cost_tool},
            now=now,
        )
        session.commit()
        raise PolicyStateError("manual approval is required for this operation")
    if _money(request.estimated_cost) > _money(settings.manual_approval_cost_threshold) and not request.manual_approval_id:
        _append_guardrail_incident(
            session,
            incident_type="APPROVAL_REQUIRED",
            idempotency_key=request.idempotency_key,
            user_id=request.user_id,
            tenant_id=identity["tenant_id"],
            session_id=identity["session_id"],
            agent_run_id=identity["agent_run_id"],
            workflow_step=identity["workflow_step"],
            details={"reason": "cost_threshold_exceeded", "estimated_cost": str(_money(request.estimated_cost))},
            now=now,
        )
        session.commit()
        raise PolicyStateError("manual approval required above configured cost threshold")

    expires_at = now + timedelta(seconds=settings.reserve_ttl_seconds)
    trace_cap = _money(request.trace_cap or settings.default_trace_cap_amount)
    reserved_amount = _money(request.estimated_cost)

    session.execute(
        text(
            """
            INSERT INTO trace_budget_state (trace_id, cap_amount, reserved_total, settled_total, updated_at)
            VALUES (:trace_id, :cap_amount, 0.000000, 0.000000, :updated_at)
            ON CONFLICT (trace_id) DO NOTHING
            """
        ),
        {"trace_id": request.trace_id, "cap_amount": trace_cap, "updated_at": now},
    )
    current_trace = session.execute(
        text("SELECT cap_amount FROM trace_budget_state WHERE trace_id = :trace_id"),
        {"trace_id": request.trace_id},
    ).mappings().first()
    if current_trace and _money(current_trace["cap_amount"]) != trace_cap:
        raise ConflictError("trace cap mismatch for existing trace budget state")

    trace_claim = session.execute(
        text(
            """
            UPDATE trace_budget_state
            SET reserved_total = reserved_total + :reserved_amount,
                updated_at = :updated_at
            WHERE trace_id = :trace_id
              AND reserved_total + :reserved_amount <= cap_amount
            RETURNING trace_id
            """
        ),
        {
            "trace_id": request.trace_id,
            "reserved_amount": reserved_amount,
            "updated_at": now,
        },
    ).mappings().first()
    if not trace_claim:
        raise TraceCapExceededError("trace cap exceeded")

    scope_caps = _budget_caps(request, settings)
    _apply_budget_delta(
        session,
        scope_type="run",
        scope_key=identity["agent_run_id"],
        cap_amount=scope_caps["run"],
        delta_amount=reserved_amount,
        now=now,
    )
    _apply_budget_delta(
        session,
        scope_type="session",
        scope_key=identity["session_id"],
        cap_amount=scope_caps["session"],
        delta_amount=reserved_amount,
        now=now,
    )
    _apply_budget_delta(
        session,
        scope_type="user",
        scope_key=request.user_id,
        cap_amount=scope_caps["user"],
        delta_amount=reserved_amount,
        now=now,
    )
    _apply_budget_delta(
        session,
        scope_type="tenant",
        scope_key=identity["tenant_id"],
        cap_amount=scope_caps["tenant"],
        delta_amount=reserved_amount,
        now=now,
    )

    wallet = session.execute(
        text(
            """
            UPDATE user_wallets
            SET balance = balance - :reserved_amount,
                updated_at = :updated_at
            WHERE user_id = :user_id
              AND active = TRUE
              AND balance >= :reserved_amount
            RETURNING user_id
            """
        ),
        {
            "user_id": request.user_id,
            "reserved_amount": reserved_amount,
            "updated_at": now,
        },
    ).mappings().first()
    if not wallet:
        raise InsufficientFundsError("wallet inactive or insufficient balance")

    try:
        session.execute(
            text(
                """
                INSERT INTO escrow_ledger (
                    idempotency_key,
                    tenant_id,
                    user_id,
                    session_id,
                    agent_run_id,
                    workflow_step,
                    policy_version,
                    trace_id,
                    model,
                    request_fingerprint,
                    reserved_amount,
                    actual_amount,
                    status,
                    terminal_reason,
                    trace_cap_amount,
                    created_at,
                    expires_at
                ) VALUES (
                    :idempotency_key,
                    :tenant_id,
                    :user_id,
                    :session_id,
                    :agent_run_id,
                    :workflow_step,
                    :policy_version,
                    :trace_id,
                    :model,
                    :request_fingerprint,
                    :reserved_amount,
                    0.000000,
                    'RESERVED',
                    'RESERVE_CREATED',
                    :trace_cap_amount,
                    :created_at,
                    :expires_at
                )
                """
            ),
            {
                "idempotency_key": request.idempotency_key,
                "tenant_id": identity["tenant_id"],
                "user_id": request.user_id,
                "session_id": identity["session_id"],
                "agent_run_id": identity["agent_run_id"],
                "workflow_step": identity["workflow_step"],
                "policy_version": request.policy_version,
                "trace_id": request.trace_id,
                "model": request.model,
                "request_fingerprint": fingerprint,
                "reserved_amount": reserved_amount,
                "trace_cap_amount": trace_cap,
                "created_at": now,
                "expires_at": expires_at,
            },
        )
    except IntegrityError as exc:
        raise ConflictError("idempotency key already exists") from exc

    _append_event(
        session,
        idempotency_key=request.idempotency_key,
        user_id=request.user_id,
        event_type="RESERVE_CREATED",
        amount_delta=-reserved_amount,
        metadata={
            "trace_id": request.trace_id,
            "model": request.model,
            "trace_cap_amount": str(trace_cap),
            "tenant_id": identity["tenant_id"],
            "session_id": identity["session_id"],
            "agent_run_id": identity["agent_run_id"],
            "workflow_step": identity["workflow_step"],
            "policy_version": request.policy_version,
        },
    )
    _record_lineage(
        session,
        idempotency_key=request.idempotency_key,
        identity=identity,
        user_id=request.user_id,
        event_type="RESERVE_CREATED",
        request=request,
        provider_request_id=None,
        state_snapshot={"status": "RESERVED", "reserved_amount": str(reserved_amount)},
        now=now,
    )
    session.commit()

    return OperationResult(
        idempotency_key=request.idempotency_key,
        status="RESERVED",
        actual_amount=reserved_amount,
    )


def apply_settlement(session: Session, settings: Settings, request: SettleRequest) -> OperationResult:
    operation = _load_operation_for_update(
        session,
        idempotency_key=request.idempotency_key,
        provider_request_id=request.provider_request_id,
    )
    if not operation:
        raise NotFoundError("reservation not found")

    if request.idempotency_key and request.idempotency_key != operation["idempotency_key"]:
        raise ConflictError("provider request id resolves to a different logical operation")
    _validate_settlement_identity(operation, request)

    if request.outcome == "SETTLED":
        result = _finalize_settlement(session, settings, operation, request)
    else:
        result = _record_attempt_state(session, operation, request)

    session.commit()
    return result


def _record_attempt_state(session: Session, operation: dict, request: SettleRequest) -> OperationResult:
    if operation["status"] in {"SETTLED", "EXPIRED"}:
        raise PolicyStateError("cannot record dispatch activity for a terminal operation")

    if not request.dispatch_attempt_key:
        raise PolicyStateError("dispatch_attempt_key is required for non-terminal execution updates")

    now = _utcnow()
    _enforce_loop_guardrail(session, operation, request, now)
    _upsert_attempt(session, operation["idempotency_key"], request, now)

    status = request.outcome
    reason = request.reason or request.outcome
    session.execute(
        text(
            """
            UPDATE escrow_ledger
            SET status = :status,
                dispatch_started_at = COALESCE(dispatch_started_at, :dispatch_started_at),
                provider_request_id = COALESCE(:provider_request_id, provider_request_id),
                terminal_reason = :terminal_reason,
                input_tokens = :input_tokens,
                output_tokens = :output_tokens,
                cached_input_tokens = :cached_input_tokens,
                cached_output_tokens = :cached_output_tokens,
                latency_ms = :latency_ms,
                retry_count = :retry_count,
                failover_count = :failover_count,
                prompt_template_version = COALESCE(:prompt_template_version, prompt_template_version),
                system_context_hash = COALESCE(:system_context_hash, system_context_hash),
                tool_name = COALESCE(:tool_name, tool_name),
                raw_tool_output = COALESCE(:raw_tool_output, raw_tool_output)
            WHERE idempotency_key = :idempotency_key
            """
        ),
        {
            "status": status,
            "dispatch_started_at": now,
            "provider_request_id": request.provider_request_id,
            "terminal_reason": reason,
            "input_tokens": request.input_tokens,
            "output_tokens": request.output_tokens,
            "cached_input_tokens": request.cached_input_tokens,
            "cached_output_tokens": request.cached_output_tokens,
            "latency_ms": request.latency_ms,
            "retry_count": request.retry_count,
            "failover_count": request.failover_count,
            "prompt_template_version": request.prompt_template_version,
            "system_context_hash": request.system_context_hash,
            "tool_name": request.tool_name,
            "raw_tool_output": request.raw_tool_output,
            "idempotency_key": operation["idempotency_key"],
        },
    )
    event_type = "DISPATCH_STARTED" if status == "IN_FLIGHT" else "PROVIDER_TIMEOUT_RECORDED"
    _append_event(
        session,
        idempotency_key=operation["idempotency_key"],
        user_id=operation["user_id"],
        event_type=event_type,
        amount_delta=Decimal("0"),
        metadata={
            "dispatch_attempt_key": request.dispatch_attempt_key,
            "provider_name": request.provider_name,
            "provider_request_id": request.provider_request_id,
            "reason": reason,
            "tenant_id": operation["tenant_id"],
            "session_id": operation["session_id"],
            "agent_run_id": operation["agent_run_id"],
            "workflow_step": operation["workflow_step"],
            "input_tokens": request.input_tokens,
            "output_tokens": request.output_tokens,
            "cached_input_tokens": request.cached_input_tokens,
            "cached_output_tokens": request.cached_output_tokens,
            "latency_ms": request.latency_ms,
            "retry_count": request.retry_count,
            "failover_count": request.failover_count,
        },
    )
    _record_lineage(
        session,
        idempotency_key=operation["idempotency_key"],
        identity=_identity_from_operation(operation),
        user_id=operation["user_id"],
        event_type=event_type,
        request=request,
        provider_request_id=request.provider_request_id,
        state_snapshot=request.state_snapshot
        or {
            "status": status,
            "reason": reason,
            "retry_count": request.retry_count,
            "failover_count": request.failover_count,
        },
        now=now,
    )
    return OperationResult(
        idempotency_key=operation["idempotency_key"],
        status=status,
        actual_amount=_money(operation["actual_amount"]),
    )


def _finalize_settlement(
    session: Session, settings: Settings, operation: dict, request: SettleRequest
) -> OperationResult:
    actual_amount = _money(request.actual_cost)

    if operation["status"] == "SETTLED":
        provider_matches = (
            not request.provider_request_id
            or request.provider_request_id == operation["provider_request_id"]
        )
        if provider_matches and _money(operation["actual_amount"]) == actual_amount:
            return OperationResult(
                idempotency_key=operation["idempotency_key"],
                status="SETTLED",
                actual_amount=actual_amount,
            )
        raise ConflictError("settlement replay does not match the recorded terminal state")

    now = _utcnow()
    if request.dispatch_attempt_key:
        _upsert_attempt(session, operation["idempotency_key"], request, now)

    reserved_amount = _money(operation["reserved_amount"])
    previous_status = operation["status"]
    late_after_expiry = previous_status in {"EXPIRED", "STRANDED"}
    reserved_still_held = previous_status not in {"EXPIRED"}

    refund_amount = Decimal("0")
    correction_debit = Decimal("0")
    if reserved_still_held:
        if actual_amount <= reserved_amount:
            refund_amount = _money(reserved_amount - actual_amount)
        else:
            correction_debit = _money(actual_amount - reserved_amount)
    else:
        correction_debit = actual_amount

    budget_delta = actual_amount
    if reserved_still_held:
        budget_delta = _money(actual_amount - reserved_amount)

    if refund_amount:
        session.execute(
            text(
                """
                UPDATE user_wallets
                SET balance = balance + :refund_amount,
                    updated_at = :updated_at
                WHERE user_id = :user_id
                """
            ),
            {
                "refund_amount": refund_amount,
                "updated_at": now,
                "user_id": operation["user_id"],
            },
        )
        _append_event(
            session,
            idempotency_key=operation["idempotency_key"],
            user_id=operation["user_id"],
            event_type="SETTLEMENT_REFUND",
            amount_delta=refund_amount,
            metadata={"reason": "unused_reserve_refund"},
        )

    if correction_debit:
        session.execute(
            text(
                """
                UPDATE user_wallets
                SET balance = balance - :correction_debit,
                    updated_at = :updated_at
                WHERE user_id = :user_id
                """
            ),
            {
                "correction_debit": correction_debit,
                "updated_at": now,
                "user_id": operation["user_id"],
            },
        )
        _append_event(
            session,
            idempotency_key=operation["idempotency_key"],
            user_id=operation["user_id"],
            event_type="SETTLEMENT_CORRECTION_DEBIT",
            amount_delta=-correction_debit,
            metadata={
                "reason": "authoritative_provider_settlement",
                "late_after_expiry": late_after_expiry,
            },
        )

    if reserved_still_held:
        session.execute(
            text(
                """
                UPDATE trace_budget_state
                SET reserved_total = reserved_total - :reserved_amount,
                    settled_total = settled_total + :actual_amount,
                    updated_at = :updated_at
                WHERE trace_id = :trace_id
                """
            ),
            {
                "reserved_amount": reserved_amount,
                "actual_amount": actual_amount,
                "updated_at": now,
                "trace_id": operation["trace_id"],
            },
        )
    else:
        session.execute(
            text(
                """
                UPDATE trace_budget_state
                SET settled_total = settled_total + :actual_amount,
                    updated_at = :updated_at
                WHERE trace_id = :trace_id
                """
            ),
            {
                "actual_amount": actual_amount,
                "updated_at": now,
                "trace_id": operation["trace_id"],
            },
        )

    if budget_delta:
        scope_caps = _budget_caps_from_operation(operation, settings)
        _apply_budget_delta(
            session,
            scope_type="run",
            scope_key=operation["agent_run_id"],
            cap_amount=scope_caps["run"],
            delta_amount=budget_delta,
            now=now,
        )
        _apply_budget_delta(
            session,
            scope_type="session",
            scope_key=operation["session_id"],
            cap_amount=scope_caps["session"],
            delta_amount=budget_delta,
            now=now,
        )
        _apply_budget_delta(
            session,
            scope_type="user",
            scope_key=operation["user_id"],
            cap_amount=scope_caps["user"],
            delta_amount=budget_delta,
            now=now,
        )
        _apply_budget_delta(
            session,
            scope_type="tenant",
            scope_key=operation["tenant_id"],
            cap_amount=scope_caps["tenant"],
            delta_amount=budget_delta,
            now=now,
        )

    drift_amount = _money(actual_amount - reserved_amount)
    terminal_reason = "SETTLED_FINAL"
    if late_after_expiry:
        terminal_reason = "RECONCILED_LATE_SETTLE"

    session.execute(
        text(
            """
            UPDATE escrow_ledger
            SET status = 'SETTLED',
                actual_amount = :actual_amount,
                provider_request_id = COALESCE(:provider_request_id, provider_request_id),
                terminal_reason = :terminal_reason,
                settled_at = :settled_at,
                drift_amount = :drift_amount,
                policy_version = :policy_version,
                input_tokens = :input_tokens,
                output_tokens = :output_tokens,
                cached_input_tokens = :cached_input_tokens,
                cached_output_tokens = :cached_output_tokens,
                latency_ms = :latency_ms,
                retry_count = :retry_count,
                failover_count = :failover_count,
                prompt_template_version = COALESCE(:prompt_template_version, prompt_template_version),
                system_context_hash = COALESCE(:system_context_hash, system_context_hash),
                tool_name = COALESCE(:tool_name, tool_name),
                raw_tool_output = COALESCE(:raw_tool_output, raw_tool_output)
            WHERE idempotency_key = :idempotency_key
            """
        ),
        {
            "actual_amount": actual_amount,
            "provider_request_id": request.provider_request_id,
            "terminal_reason": terminal_reason,
            "settled_at": now,
            "drift_amount": drift_amount,
            "policy_version": request.policy_version or operation.get("policy_version") or "v1",
            "input_tokens": request.input_tokens,
            "output_tokens": request.output_tokens,
            "cached_input_tokens": request.cached_input_tokens,
            "cached_output_tokens": request.cached_output_tokens,
            "latency_ms": request.latency_ms,
            "retry_count": request.retry_count,
            "failover_count": request.failover_count,
            "prompt_template_version": request.prompt_template_version,
            "system_context_hash": request.system_context_hash,
            "tool_name": request.tool_name,
            "raw_tool_output": request.raw_tool_output,
            "idempotency_key": operation["idempotency_key"],
        },
    )

    _append_event(
        session,
        idempotency_key=operation["idempotency_key"],
        user_id=operation["user_id"],
        event_type=terminal_reason,
        amount_delta=Decimal("0"),
        metadata={
            "provider_request_id": request.provider_request_id,
            "dispatch_attempt_key": request.dispatch_attempt_key,
            "previous_status": previous_status,
            "tenant_id": operation["tenant_id"],
            "session_id": operation["session_id"],
            "agent_run_id": operation["agent_run_id"],
            "workflow_step": operation["workflow_step"],
            "input_tokens": request.input_tokens,
            "output_tokens": request.output_tokens,
            "cached_input_tokens": request.cached_input_tokens,
            "cached_output_tokens": request.cached_output_tokens,
            "latency_ms": request.latency_ms,
        },
    )
    _record_lineage(
        session,
        idempotency_key=operation["idempotency_key"],
        identity=_identity_from_operation(operation),
        user_id=operation["user_id"],
        event_type=terminal_reason,
        request=request,
        provider_request_id=request.provider_request_id,
        state_snapshot=request.state_snapshot
        or {
            "status": "SETTLED",
            "actual_amount": str(actual_amount),
            "reserved_amount": str(reserved_amount),
            "drift_amount": str(drift_amount),
        },
        now=now,
    )

    drift_excess = max(Decimal("0"), drift_amount)
    if drift_excess:
        if _drift_exceeds_tolerance(drift_excess, reserved_amount, settings):
            session.execute(
                text(
                    """
                    UPDATE user_wallets
                    SET active = FALSE,
                        locked_at = :locked_at,
                        lock_reason = :lock_reason,
                        updated_at = :updated_at
                    WHERE user_id = :user_id
                    """
                ),
                {
                    "locked_at": now,
                    "lock_reason": "DRIFT_THRESHOLD_EXCEEDED",
                    "updated_at": now,
                    "user_id": operation["user_id"],
                },
            )
            _append_event(
                session,
                idempotency_key=operation["idempotency_key"],
                user_id=operation["user_id"],
                event_type="DRIFT_ENFORCED",
                amount_delta=Decimal("0"),
                metadata={
                    "drift_amount": str(drift_excess),
                    "threshold_absolute": str(_money(settings.drift_absolute_tolerance)),
                    "threshold_ratio": str(_money(settings.drift_ratio_tolerance)),
                },
            )
        else:
            _append_event(
                session,
                idempotency_key=operation["idempotency_key"],
                user_id=operation["user_id"],
                event_type="DRIFT_TOLERATED",
                amount_delta=Decimal("0"),
                metadata={"drift_amount": str(drift_excess)},
            )

    return OperationResult(
        idempotency_key=operation["idempotency_key"],
        status="SETTLED",
        actual_amount=actual_amount,
    )


def expire_operation(session: Session, operation: dict, reason: str) -> None:
    now = _utcnow()
    reserved_amount = _money(operation["reserved_amount"])
    if operation["status"] in {"IN_FLIGHT", "PROVIDER_TIMEOUT"} or _has_open_attempts(
        session, operation["idempotency_key"]
    ):
        session.execute(
            text(
                """
                UPDATE escrow_ledger
                SET status = 'STRANDED',
                    expired_at = :expired_at,
                    terminal_reason = :terminal_reason
                WHERE idempotency_key = :idempotency_key
                """
            ),
            {
                "expired_at": now,
                "terminal_reason": "STRANDED_HOLD_PENDING_RECONCILIATION",
                "idempotency_key": operation["idempotency_key"],
            },
        )
        _append_event(
            session,
            idempotency_key=operation["idempotency_key"],
            user_id=operation["user_id"],
            event_type="STRANDED_HOLD",
            amount_delta=Decimal("0"),
            metadata={"reason": reason},
        )
        return

    session.execute(
        text(
            """
            UPDATE user_wallets
            SET balance = balance + :reserved_amount,
                updated_at = :updated_at
            WHERE user_id = :user_id
            """
        ),
        {
            "reserved_amount": reserved_amount,
            "updated_at": now,
            "user_id": operation["user_id"],
        },
    )
    session.execute(
        text(
            """
            UPDATE trace_budget_state
            SET reserved_total = reserved_total - :reserved_amount,
                updated_at = :updated_at
            WHERE trace_id = :trace_id
            """
        ),
        {
            "reserved_amount": reserved_amount,
            "updated_at": now,
            "trace_id": operation["trace_id"],
        },
    )
    session.execute(
        text(
            """
            UPDATE escrow_ledger
            SET status = 'EXPIRED',
                expired_at = :expired_at,
                terminal_reason = :terminal_reason
            WHERE idempotency_key = :idempotency_key
            """
        ),
        {
            "expired_at": now,
            "terminal_reason": reason,
            "idempotency_key": operation["idempotency_key"],
        },
    )
    _append_event(
        session,
        idempotency_key=operation["idempotency_key"],
        user_id=operation["user_id"],
        event_type="EXPIRED_SWEEP",
        amount_delta=reserved_amount,
        metadata={"reason": reason},
    )


def _has_open_attempts(session: Session, idempotency_key: str) -> bool:
    row = session.execute(
        text(
            """
            SELECT 1
            FROM provider_dispatch_attempts
            WHERE idempotency_key = :idempotency_key
              AND status IN ('IN_FLIGHT', 'PROVIDER_TIMEOUT')
            LIMIT 1
            """
        ),
        {"idempotency_key": idempotency_key},
    ).first()
    return row is not None


def _upsert_attempt(session: Session, idempotency_key: str, request: SettleRequest, now: datetime) -> None:
    try:
        session.execute(
            text(
                """
                INSERT INTO provider_dispatch_attempts (
                    attempt_key,
                    idempotency_key,
                    provider_name,
                    model_name,
                    provider_request_id,
                    status,
                    terminal_reason,
                    created_at,
                    updated_at
                ) VALUES (
                    :attempt_key,
                    :idempotency_key,
                    :provider_name,
                    :model_name,
                    :provider_request_id,
                    :status,
                    :terminal_reason,
                    :created_at,
                    :updated_at
                )
                ON CONFLICT (attempt_key) DO UPDATE SET
                    provider_name = excluded.provider_name,
                    model_name = excluded.model_name,
                    provider_request_id = COALESCE(excluded.provider_request_id, provider_dispatch_attempts.provider_request_id),
                    status = excluded.status,
                    terminal_reason = excluded.terminal_reason,
                    updated_at = excluded.updated_at
                """
            ),
            {
                "attempt_key": request.dispatch_attempt_key,
                "idempotency_key": idempotency_key,
                "provider_name": request.provider_name,
                "model_name": request.model,
                "provider_request_id": request.provider_request_id,
                "status": request.outcome,
                "terminal_reason": request.reason or request.outcome,
                "created_at": now,
                "updated_at": now,
            },
        )
    except IntegrityError as exc:
        raise ConflictError("provider_request_id is already attached to a different dispatch attempt") from exc


def _load_operation_for_update(
    session: Session, idempotency_key: str | None, provider_request_id: str | None
) -> dict | None:
    lock_clause = "" if session.bind.dialect.name == "sqlite" else " FOR UPDATE"
    if idempotency_key:
        query = text(
            f"""
            SELECT *
            FROM escrow_ledger
            WHERE idempotency_key = :idempotency_key
            {lock_clause}
            """
        )
        return session.execute(query, {"idempotency_key": idempotency_key}).mappings().first()

    if provider_request_id:
        query = text(
            f"""
            SELECT e.*
            FROM escrow_ledger e
            JOIN provider_dispatch_attempts a ON a.idempotency_key = e.idempotency_key
            WHERE a.provider_request_id = :provider_request_id
            {lock_clause}
            """
        )
        return session.execute(query, {"provider_request_id": provider_request_id}).mappings().first()
    return None


def _append_event(
    session: Session,
    *,
    idempotency_key: str,
    user_id: str,
    event_type: str,
    amount_delta: Decimal,
    metadata: dict,
) -> None:
    metadata_json = json.dumps(metadata, sort_keys=True)
    metadata_value = ":metadata"
    if session.bind.dialect.name == "postgresql":
        metadata_value = "CAST(:metadata AS JSONB)"

    session.execute(
        text(
            f"""
            INSERT INTO ledger_events (idempotency_key, user_id, event_type, amount_delta, metadata)
            VALUES (:idempotency_key, :user_id, :event_type, :amount_delta, {metadata_value})
            """
        ),
        {
            "idempotency_key": idempotency_key,
            "user_id": user_id,
            "event_type": event_type,
            "amount_delta": _money(amount_delta),
            "metadata": metadata_json,
        },
    )


def _fingerprint_reserve_request(request: ReserveRequest) -> str:
    payload = {
        "estimated_cost": str(_money(request.estimated_cost)),
        "model": request.model,
        "trace_cap": str(_money(request.trace_cap)) if request.trace_cap is not None else None,
        "trace_id": request.trace_id,
        "user_id": request.user_id,
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()


def _drift_exceeds_tolerance(drift_amount: Decimal, reserved_amount: Decimal, settings: Settings) -> bool:
    absolute_threshold = _money(settings.drift_absolute_tolerance)
    ratio_threshold = _money(settings.drift_ratio_tolerance)
    if drift_amount <= absolute_threshold:
        return False
    if reserved_amount <= Decimal("0"):
        return True
    return (drift_amount / reserved_amount) > ratio_threshold


def _money(value: Decimal | str | int | float | None) -> Decimal:
    return Decimal(value or 0).quantize(MONEY_QUANTUM)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)
