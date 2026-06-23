from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .config import Settings
from .metrics import get_counters
from .schemas import (
    AdminCorrectionRequest,
    AdminCorrectionResponse,
    AuditLogEntry,
    AuditLogResponse,
    ReconciliationSummary,
    ReserveRequest,
    SettleRequest,
    SpendReportItem,
    SpendReportResponse,
    StrandedOperationSummary,
    WalletSummaryResponse,
    WalletUnlockResponse,
)

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
        get_counters().increment("reserve_idempotent_replay_total")
        return OperationResult(
            idempotency_key=existing["idempotency_key"],
            status=existing["status"],
            actual_amount=_money(existing["actual_amount"]),
        )

    now = _utcnow()
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
        },
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


def _money(value: Decimal | str | int | float | None) -> Decimal:
    return Decimal(value or 0).quantize(MONEY_QUANTUM)


def _load_json_object(value: object) -> dict:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        loaded = json.loads(value)
        return loaded if isinstance(loaded, dict) else {}
    return {}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Phase 3: Reconciliation queries and admin correction operations
# ---------------------------------------------------------------------------


def get_reconciliation_summary(session: Session) -> ReconciliationSummary:
    """Return a point-in-time ledger health snapshot for the operations dashboard.

    All queries run within the caller's session/transaction for a consistent
    read.  The summary is intended for observability only and never mutates
    state.
    """
    now = _utcnow()

    # Status breakdown across all escrow operations.
    status_rows = session.execute(
        text(
            """
            SELECT status, COUNT(*) AS cnt
            FROM escrow_ledger
            GROUP BY status
            """
        )
    ).mappings().all()

    by_status: dict[str, int] = {row["status"]: int(row["cnt"]) for row in status_rows}
    total_operations = sum(by_status.values())
    stranded_count = by_status.get("STRANDED", 0)

    stranded_reserved_row = session.execute(
        text(
            """
            SELECT COALESCE(SUM(reserved_amount), 0) AS total
            FROM escrow_ledger
            WHERE status = 'STRANDED'
            """
        )
    ).mappings().first()
    stranded_reserved_total = _money(stranded_reserved_row["total"] if stranded_reserved_row else 0)

    drift_row = session.execute(
        text(
            """
            SELECT
                COUNT(*) FILTER (WHERE event_type = 'DRIFT_ENFORCED')  AS drift_enforced,
                COUNT(*) FILTER (WHERE event_type = 'DRIFT_TOLERATED') AS drift_tolerated
            FROM ledger_events
            """
        )
    ).mappings().first()
    drift_enforced = int(drift_row["drift_enforced"]) if drift_row else 0
    drift_tolerated = int(drift_row["drift_tolerated"]) if drift_row else 0

    locked_row = session.execute(
        text(
            """
            SELECT COUNT(*) AS cnt
            FROM user_wallets
            WHERE active = FALSE AND locked_at IS NOT NULL
            """
        )
    ).mappings().first()
    locked_wallets_count = int(locked_row["cnt"]) if locked_row else 0

    anomaly_flag = stranded_count > 0 or locked_wallets_count > 0 or drift_enforced > 0

    return ReconciliationSummary(
        generated_at=now,
        total_operations=total_operations,
        by_status=by_status,
        stranded_count=stranded_count,
        stranded_reserved_total=stranded_reserved_total,
        locked_wallets_count=locked_wallets_count,
        drift_enforced_total=drift_enforced,
        drift_tolerated_total=drift_tolerated,
        anomaly_flag=anomaly_flag,
    )


def list_stranded_operations(
    session: Session, limit: int = 50, offset: int = 0
) -> list[StrandedOperationSummary]:
    """Return STRANDED operations ordered by age, oldest first.

    STRANDED operations represent ambiguous provider outcomes where the
    reconciler preserved the hold pending explicit admin review.  This query
    surfaces them for the operations dashboard.
    """
    rows = session.execute(
        text(
            """
            SELECT
                idempotency_key,
                user_id,
                trace_id,
                model,
                reserved_amount,
                created_at,
                expired_at,
                dispatch_started_at,
                terminal_reason
            FROM escrow_ledger
            WHERE status = 'STRANDED'
            ORDER BY created_at ASC
            LIMIT :limit
            OFFSET :offset
            """
        ),
        {"limit": limit, "offset": offset},
    ).mappings().all()

    return [
        StrandedOperationSummary(
            idempotency_key=row["idempotency_key"],
            user_id=row["user_id"],
            trace_id=row["trace_id"],
            model=row["model"],
            reserved_amount=_money(row["reserved_amount"]),
            created_at=row["created_at"],
            expired_at=row["expired_at"],
            dispatch_started_at=row["dispatch_started_at"],
            terminal_reason=row["terminal_reason"],
        )
        for row in rows
    ]


def list_admin_audit_log(
    session: Session,
    *,
    wallet_id: str | None = None,
    operation_id: str | None = None,
    action_type: str | None = None,
    from_timestamp: datetime | None = None,
    to_timestamp: datetime | None = None,
    limit: int = 50,
    offset: int = 0,
) -> AuditLogResponse:
    where_clauses = []
    params: dict[str, object] = {"limit": limit, "offset": offset}
    if wallet_id:
        where_clauses.append("wallet_id = :wallet_id")
        params["wallet_id"] = wallet_id
    if operation_id:
        where_clauses.append("operation_id = :operation_id")
        params["operation_id"] = operation_id
    if action_type:
        where_clauses.append("action_type = :action_type")
        params["action_type"] = action_type
    if from_timestamp:
        where_clauses.append("applied_at >= :from_timestamp")
        params["from_timestamp"] = from_timestamp
    if to_timestamp:
        where_clauses.append("applied_at <= :to_timestamp")
        params["to_timestamp"] = to_timestamp

    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
    rows = session.execute(
        text(
            f"""
            SELECT log_id, admin_user_id, action_type, subject_key, wallet_id, operation_id, details, applied_at
            FROM admin_audit_log
            {where_sql}
            ORDER BY applied_at DESC
            LIMIT :limit
            OFFSET :offset
            """
        ),
        params,
    ).mappings().all()

    total_row = session.execute(
        text(
            f"""
            SELECT COUNT(*) AS cnt
            FROM admin_audit_log
            {where_sql}
            """
        ),
        {k: v for k, v in params.items() if k not in {"limit", "offset"}},
    ).mappings().first()

    items = [
        AuditLogEntry(
            log_id=int(row["log_id"]),
            admin_user_id=row["admin_user_id"],
            action_type=row["action_type"],
            subject_key=row["subject_key"],
            wallet_id=row["wallet_id"],
            operation_id=row["operation_id"],
            details=_load_json_object(row["details"]),
            applied_at=row["applied_at"],
        )
        for row in rows
    ]
    return AuditLogResponse(
        items=items,
        total=int(total_row["cnt"]) if total_row else 0,
        limit=limit,
        offset=offset,
    )


def get_spend_report(
    session: Session,
    *,
    wallet_id: str | None = None,
    model: str | None = None,
    from_timestamp: datetime | None = None,
    to_timestamp: datetime | None = None,
) -> SpendReportResponse:
    where_clauses = ["status = 'SETTLED'"]
    params: dict[str, object] = {}
    if wallet_id:
        where_clauses.append("user_id = :wallet_id")
        params["wallet_id"] = wallet_id
    if model:
        where_clauses.append("model = :model")
        params["model"] = model
    if from_timestamp:
        where_clauses.append("COALESCE(settled_at, created_at) >= :from_timestamp")
        params["from_timestamp"] = from_timestamp
    if to_timestamp:
        where_clauses.append("COALESCE(settled_at, created_at) <= :to_timestamp")
        params["to_timestamp"] = to_timestamp

    rows = session.execute(
        text(
            f"""
            SELECT user_id AS wallet_id, model, COUNT(*) AS operations, COALESCE(SUM(actual_amount), 0) AS total_cost
            FROM escrow_ledger
            WHERE {' AND '.join(where_clauses)}
            GROUP BY user_id, model
            ORDER BY user_id ASC, model ASC
            """
        ),
        params,
    ).mappings().all()
    return SpendReportResponse(
        generated_at=_utcnow(),
        from_timestamp=from_timestamp,
        to_timestamp=to_timestamp,
        items=[
            SpendReportItem(
                wallet_id=row["wallet_id"],
                model=row["model"],
                operations=int(row["operations"]),
                total_cost=_money(row["total_cost"]),
                input_tokens=0,
                output_tokens=0,
            )
            for row in rows
        ],
    )


def get_wallet_summary(session: Session, wallet_id: str) -> WalletSummaryResponse:
    wallet = session.execute(
        text(
            """
            SELECT user_id, balance, active, lock_reason, locked_at
            FROM user_wallets
            WHERE user_id = :wallet_id
            """
        ),
        {"wallet_id": wallet_id},
    ).mappings().first()
    if not wallet:
        raise NotFoundError("wallet not found")

    reserved_row = session.execute(
        text(
            """
            SELECT COALESCE(SUM(reserved_amount), 0) AS total
            FROM escrow_ledger
            WHERE user_id = :wallet_id
              AND status IN ('RESERVED', 'IN_FLIGHT', 'PROVIDER_TIMEOUT', 'STRANDED')
            """
        ),
        {"wallet_id": wallet_id},
    ).mappings().first()
    event_row = session.execute(
        text(
            """
            SELECT event_type, recorded_at
            FROM ledger_events
            WHERE user_id = :wallet_id
            ORDER BY recorded_at DESC, event_id DESC
            LIMIT 1
            """
        ),
        {"wallet_id": wallet_id},
    ).mappings().first()
    return WalletSummaryResponse(
        wallet_id=wallet_id,
        balance=_money(wallet["balance"]),
        reserved_total=_money(reserved_row["total"] if reserved_row else 0),
        locked=not bool(wallet["active"]),
        lock_reason=wallet["lock_reason"],
        locked_at=wallet["locked_at"],
        last_event_type=event_row["event_type"] if event_row else None,
        last_event_at=event_row["recorded_at"] if event_row else None,
    )


def apply_admin_correction(
    session: Session, settings: Settings, request: AdminCorrectionRequest
) -> AdminCorrectionResponse:
    """Administratively settle a STRANDED or EXPIRED operation.

    This function resolves an ambiguous operation by applying the
    authoritative provider cost supplied by the admin.  The existing
    settlement finalization path is reused so that all balance mutations,
    trace-budget updates, and audit events follow the same deterministic
    rules as normal settlement.

    An additional ADMIN_CORRECTION_APPLIED event is appended to the
    ledger_events table and a row is written to admin_audit_log so that
    the admin action is independently traceable.
    """
    operation = _load_operation_for_update(
        session,
        idempotency_key=request.idempotency_key,
        provider_request_id=None,
    )
    if not operation:
        raise NotFoundError("operation not found")

    previous_status = operation["status"]
    if previous_status not in {"STRANDED", "EXPIRED"}:
        raise PolicyStateError(
            f"admin correction requires STRANDED or EXPIRED status; got {previous_status}"
        )

    # Build a synthetic settle request reusing the existing finalization path.
    settle_req = SettleRequest(
        idempotency_key=request.idempotency_key,
        outcome="SETTLED",
        actual_cost=request.actual_amount,
        dispatch_attempt_key=request.dispatch_attempt_key,
        provider_name=request.provider_name,
        reason=f"ADMIN_CORRECTION: {request.admin_reason}",
    )
    result = _finalize_settlement(session, settings, dict(operation), settle_req)

    # Append operation-level admin correction event to the audit trail.
    _append_event(
        session,
        idempotency_key=request.idempotency_key,
        user_id=operation["user_id"],
        event_type="ADMIN_CORRECTION_APPLIED",
        amount_delta=Decimal("0"),
        metadata={
            "admin_user_id": request.admin_user_id,
            "admin_reason": request.admin_reason,
            "previous_status": previous_status,
            "corrected_amount": str(result.actual_amount),
        },
    )

    # Write to admin_audit_log (not subject to escrow_ledger FK constraints
    # so that wallet-level events can also be stored in the same table).
    _append_admin_log(
        session,
        admin_user_id=request.admin_user_id,
        action_type="OPERATION_CORRECTION",
        subject_key=request.idempotency_key,
        wallet_id=operation["user_id"],
        operation_id=request.idempotency_key,
        details={
            "previous_status": previous_status,
            "corrected_amount": str(result.actual_amount),
            "admin_reason": request.admin_reason,
        },
    )

    session.commit()
    return AdminCorrectionResponse(
        idempotency_key=request.idempotency_key,
        previous_status=previous_status,
        status="SETTLED",
        actual_amount=result.actual_amount,
        correction_applied=True,
    )


def unlock_wallet(
    session: Session,
    user_id: str,
    admin_user_id: str,
    admin_reason: str,
) -> WalletUnlockResponse:
    """Unlock a wallet that was locked by drift-threshold enforcement.

    The action is append-only in the sense that the admin_audit_log receives
    a permanent record even though the user_wallets row is updated.
    """
    wallet = session.execute(
        text(
            """
            SELECT user_id, active, locked_at, lock_reason
            FROM user_wallets
            WHERE user_id = :user_id
            """
        ),
        {"user_id": user_id},
    ).mappings().first()

    if not wallet:
        raise NotFoundError("wallet not found")

    if wallet["active"]:
        return WalletUnlockResponse(
            user_id=user_id,
            unlocked=False,
            message="wallet is already active — no action taken",
        )

    now = _utcnow()
    session.execute(
        text(
            """
            UPDATE user_wallets
            SET active = TRUE,
                locked_at = NULL,
                lock_reason = NULL,
                updated_at = :updated_at
            WHERE user_id = :user_id
            """
        ),
        {"user_id": user_id, "updated_at": now},
    )

    _append_admin_log(
        session,
        admin_user_id=admin_user_id,
        action_type="WALLET_UNLOCK",
        subject_key=user_id,
        wallet_id=user_id,
        operation_id=None,
        details={
            "previous_lock_reason": wallet["lock_reason"],
            "admin_reason": admin_reason,
        },
    )

    session.commit()
    return WalletUnlockResponse(
        user_id=user_id,
        unlocked=True,
        message="wallet unlocked and reactivated",
    )


def _append_admin_log(
    session: Session,
    *,
    admin_user_id: str,
    action_type: str,
    subject_key: str,
    wallet_id: str | None,
    operation_id: str | None,
    details: dict,
) -> None:
    """Insert a row into admin_audit_log."""
    details_json = json.dumps(details, sort_keys=True)
    details_value = ":details"
    if session.bind.dialect.name == "postgresql":
        details_value = "CAST(:details AS JSONB)"

    session.execute(
        text(
            f"""
            INSERT INTO admin_audit_log (
                admin_user_id,
                action_type,
                subject_key,
                wallet_id,
                operation_id,
                details
            )
            VALUES (
                :admin_user_id,
                :action_type,
                :subject_key,
                :wallet_id,
                :operation_id,
                {details_value}
            )
            """
        ),
        {
            "admin_user_id": admin_user_id,
            "action_type": action_type,
            "subject_key": subject_key,
            "wallet_id": wallet_id,
            "operation_id": operation_id,
            "details": details_json,
        },
    )
