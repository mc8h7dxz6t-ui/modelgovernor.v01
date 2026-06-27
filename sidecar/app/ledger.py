from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .config import Settings
from .metrics import get_counters
from .schemas import ReserveRequest, SettleRequest

try:
    from . import attribution
except ImportError:  # pragma: no cover
    attribution = None  # type: ignore[assignment]

from .money import quantize_money as _money

logger = logging.getLogger(__name__)


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
    fingerprint = _fingerprint_reserve_request(request)
    existing = session.execute(
        text(
            """
            SELECT idempotency_key, status, actual_amount, reserved_amount, request_fingerprint
            FROM escrow_ledger
            WHERE idempotency_key = :idempotency_key
            """
        ),
        {"idempotency_key": request.idempotency_key},
    ).mappings().first()
    if existing:
        if existing["request_fingerprint"] != fingerprint:
            raise ConflictError("idempotency key replay does not match original reserve request")
        get_counters().increment("reserve_idempotent_replay_total")
        replay_amount = existing["actual_amount"]
        if existing["status"] != "SETTLED" and _money(replay_amount) == Decimal("0"):
            replay_amount = existing["reserved_amount"]
        return OperationResult(
            idempotency_key=existing["idempotency_key"],
            status=existing["status"],
            actual_amount=_money(replay_amount),
        )

    now = _utcnow()
    _assert_circuit_closed(request.model)
    identity = (
        attribution.identity_from_reserve(request)
        if attribution and attribution.schema_supports_attribution(session)
        else None
    )
    if identity and attribution:
        try:
            attribution.enforce_manual_approval(session, settings, request, identity, now)
            attribution.apply_reserve_budget_scopes(
                session, settings, request, identity, _money(request.estimated_cost), now
            )
        except attribution.BudgetScopeExceededError as exc:
            get_counters().increment("reserve_denied_trace_cap_total")
            raise TraceCapExceededError(str(exc)) from exc
        except attribution.AttributionPolicyError as exc:
            raise PolicyStateError(str(exc)) from exc

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
        get_counters().increment("trace_cap_overrun_detected_total")
        get_counters().increment("reserve_denied_trace_cap_total")
        raise TraceCapExceededError("trace cap exceeded")

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
        get_counters().increment("reserve_denied_balance_total")
        raise InsufficientFundsError("wallet inactive or insufficient balance")

    try:
        if identity and attribution:
            session.execute(
                text(
                    """
                    INSERT INTO escrow_ledger (
                        idempotency_key, tenant_id, user_id, session_id, agent_run_id,
                        workflow_step, policy_version, trace_id, model, request_fingerprint,
                        reserved_amount, actual_amount, status, terminal_reason,
                        trace_cap_amount, created_at, expires_at
                    ) VALUES (
                        :idempotency_key, :tenant_id, :user_id, :session_id, :agent_run_id,
                        :workflow_step, :policy_version, :trace_id, :model, :request_fingerprint,
                        :reserved_amount, 0.000000, 'RESERVED', 'RESERVE_CREATED',
                        :trace_cap_amount, :created_at, :expires_at
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
        else:
            session.execute(
                text(
                    """
                    INSERT INTO escrow_ledger (
                        idempotency_key,
                        user_id,
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
                        :user_id,
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
                    "user_id": request.user_id,
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

    event_metadata = {
        "trace_id": request.trace_id,
        "model": request.model,
        "trace_cap_amount": str(trace_cap),
    }
    if identity:
        event_metadata.update(identity)
        event_metadata["policy_version"] = request.policy_version

    _append_event(
        session,
        idempotency_key=request.idempotency_key,
        user_id=request.user_id,
        event_type="RESERVE_CREATED",
        amount_delta=-reserved_amount,
        metadata=event_metadata,
    )
    if identity and attribution:
        attribution.record_lineage(
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
    get_counters().increment("reserve_success_total")

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
    if attribution and attribution.schema_supports_attribution(session):
        try:
            attribution.validate_settlement_identity(operation, request)
        except attribution.AttributionPolicyError as exc:
            raise PolicyStateError(str(exc)) from exc

    if request.outcome == "SETTLED":
        result = _finalize_settlement(session, settings, operation, request)
        session.commit()
        _release_inflight_guardrail(operation["user_id"])
        return result

    result = _record_attempt_state(session, settings, operation, request)
    if request.outcome == "PROVIDER_TIMEOUT" and request.provider_name:
        _record_provider_failure(request.provider_name)
    session.commit()
    return result


def _record_attempt_state(
    session: Session, settings: Settings, operation: dict, request: SettleRequest
) -> OperationResult:
    if operation["status"] in {"SETTLED", "EXPIRED"}:
        raise PolicyStateError("cannot record dispatch activity for a terminal operation")

    if not request.dispatch_attempt_key:
        raise PolicyStateError("dispatch_attempt_key is required for non-terminal execution updates")

    now = _utcnow()
    if attribution and attribution.schema_supports_attribution(session):
        try:
            attribution.enforce_loop_guardrail(session, operation, request, settings, now)
        except attribution.AttributionPolicyError as exc:
            raise PolicyStateError(str(exc)) from exc
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
                terminal_reason = :terminal_reason
            WHERE idempotency_key = :idempotency_key
            """
        ),
        {
            "status": status,
            "dispatch_started_at": now,
            "provider_request_id": request.provider_request_id,
            "terminal_reason": reason,
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
        },
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

    budget_delta = Decimal("0")
    if reserved_still_held:
        budget_delta = _money(actual_amount - reserved_amount)
    elif actual_amount:
        budget_delta = actual_amount
    if attribution and attribution.schema_supports_attribution(session) and budget_delta:
        try:
            attribution.apply_settlement_budget_scopes(
                session, settings, operation, budget_delta, now
            )
        except attribution.BudgetScopeExceededError as exc:
            raise TraceCapExceededError(str(exc)) from exc

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
                drift_amount = :drift_amount
            WHERE idempotency_key = :idempotency_key
            """
        ),
        {
            "actual_amount": actual_amount,
            "provider_request_id": request.provider_request_id,
            "terminal_reason": terminal_reason,
            "settled_at": now,
            "drift_amount": drift_amount,
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
        },
    )
    _detect_duplicate_settlement_events(session, operation["idempotency_key"])
    _enforce_non_negative_wallet_balance(session, operation["user_id"])
    provider_key = request.provider_name or operation.get("model") or "unknown"
    _record_provider_success(provider_key)
    if attribution and attribution.schema_supports_attribution(session):
        attribution.record_lineage(
            session,
            idempotency_key=operation["idempotency_key"],
            identity=attribution.identity_from_operation(operation),
            user_id=operation["user_id"],
            event_type=terminal_reason,
            request=request,
            provider_request_id=request.provider_request_id,
            state_snapshot={
                "status": "SETTLED",
                "actual_amount": str(actual_amount),
                "reserved_amount": str(reserved_amount),
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
            get_counters().increment("drift_enforced_total")
        else:
            _append_event(
                session,
                idempotency_key=operation["idempotency_key"],
                user_id=operation["user_id"],
                event_type="DRIFT_TOLERATED",
                amount_delta=Decimal("0"),
                metadata={"drift_amount": str(drift_excess)},
            )
            get_counters().increment("drift_tolerated_total")

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


def _ledger_events_support_tenant_id(session: Session) -> bool:
    if session.bind.dialect.name == "sqlite":
        rows = session.execute(text("PRAGMA table_info(ledger_events)")).fetchall()
        return any(row[1] == "tenant_id" for row in rows)
    found = session.execute(
        text(
            """
            SELECT 1
            FROM information_schema.columns
            WHERE table_name = 'ledger_events' AND column_name = 'tenant_id'
            """
        )
    ).first()
    return found is not None


def _resolve_event_tenant_id(session: Session, idempotency_key: str) -> str:
    if attribution and attribution.schema_supports_attribution(session):
        row = session.execute(
            text("SELECT tenant_id FROM escrow_ledger WHERE idempotency_key = :idempotency_key"),
            {"idempotency_key": idempotency_key},
        ).mappings().first()
        if row and row.get("tenant_id"):
            return str(row["tenant_id"])
    return "default-tenant"


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

    tenant_column = ""
    tenant_value = ""
    params: dict = {
        "idempotency_key": idempotency_key,
        "user_id": user_id,
        "event_type": event_type,
        "amount_delta": _money(amount_delta),
        "metadata": metadata_json,
    }
    if _ledger_events_support_tenant_id(session):
        tenant_column = ", tenant_id"
        tenant_value = ", :tenant_id"
        params["tenant_id"] = _resolve_event_tenant_id(session, idempotency_key)

    session.execute(
        text(
            f"""
            INSERT INTO ledger_events (idempotency_key, user_id, event_type, amount_delta, metadata{tenant_column})
            VALUES (:idempotency_key, :user_id, :event_type, :amount_delta, {metadata_value}{tenant_value})
            """
        ),
        params,
    )
    _maybe_seal_event(
        session,
        idempotency_key=idempotency_key,
        user_id=user_id,
        event_type=event_type,
        amount_delta=_money(amount_delta),
        metadata=metadata,
    )


def _maybe_seal_event(
    session: Session,
    *,
    idempotency_key: str,
    user_id: str,
    event_type: str,
    amount_delta: Decimal,
    metadata: dict,
) -> None:
    from . import ledger_seal
    from .metrics import get_counters

    if not ledger_seal.schema_supports_ledger_seal(session):
        return

    dialect = session.bind.dialect.name
    recorded_expr = "recorded_at::text" if dialect == "postgresql" else "recorded_at"

    try:
        row = session.execute(
            text(
                f"""
                SELECT event_id, {recorded_expr} AS recorded_at
                FROM ledger_events
                WHERE idempotency_key = :idempotency_key
                ORDER BY event_id DESC
                LIMIT 1
                """
            ),
            {"idempotency_key": idempotency_key},
        ).mappings().first()
        if not row:
            return
        ledger_seal.seal_ledger_event(
            session,
            event_id=int(row["event_id"]),
            idempotency_key=idempotency_key,
            user_id=user_id,
            event_type=event_type,
            amount_delta=str(amount_delta),
            metadata=metadata,
            recorded_at=str(row["recorded_at"]),
        )
        get_counters().increment("ledger_event_sealed_total")
    except Exception as exc:
        get_counters().increment("ledger_event_seal_failed_total")
        logger.warning("ledger event seal failed idempotency_key=%s: %s", idempotency_key, exc)


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


def _detect_duplicate_settlement_events(session: Session, idempotency_key: str) -> None:
    row = session.execute(
        text(
            """
            SELECT COUNT(*) AS cnt
            FROM ledger_events
            WHERE idempotency_key = :idempotency_key
              AND event_type IN ('SETTLED_FINAL', 'RECONCILED_LATE_SETTLE')
            """
        ),
        {"idempotency_key": idempotency_key},
    ).mappings().first()
    if row and int(row["cnt"]) > 1:
        get_counters().increment("duplicate_settlement_anomaly_total")


def _enforce_non_negative_wallet_balance(session: Session, user_id: str) -> None:
    row = session.execute(
        text(
            """
            SELECT balance
            FROM user_wallets
            WHERE user_id = :user_id
            """
        ),
        {"user_id": user_id},
    ).mappings().first()
    if row and _money(row["balance"]) < Decimal("0"):
        get_counters().increment("negative_wallet_detected_total")
        raise LedgerError("wallet balance invariant violated: negative balance detected")


def _release_inflight_guardrail(user_id: str) -> None:
    try:
        from .guardrails import get_guardrails

        get_guardrails().release_reserve(user_id=user_id)
    except Exception:
        pass


def _assert_circuit_closed(provider_key: str) -> None:
    try:
        from .circuit_breaker import CircuitOpenError, get_circuit_breaker

        get_circuit_breaker().assert_closed(provider_key)
    except CircuitOpenError:
        raise PolicyStateError(f"provider circuit open for {provider_key}") from None
    except Exception:
        pass


def _record_provider_failure(provider_name: str) -> None:
    try:
        from .circuit_breaker import get_circuit_breaker

        get_circuit_breaker().record_failure(provider_name)
    except Exception:
        pass


def _record_provider_success(provider_name: str) -> None:
    try:
        from .circuit_breaker import get_circuit_breaker

        get_circuit_breaker().record_success(provider_name)
    except Exception:
        pass



def _utcnow() -> datetime:
    return datetime.now(timezone.utc)
