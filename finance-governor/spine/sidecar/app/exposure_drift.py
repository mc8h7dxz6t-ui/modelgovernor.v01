"""Exposure drift enforcement on commit — port of ModelGovernor ledger drift lockout."""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.orm import Session

from .config import Settings
from .currency import quantize_money
from .decision_seal import append_decision_event
from .guardrail_incidents import record_guardrail_incident
from .metrics import get_counters


def drift_exceeds_tolerance(drift_amount: Decimal, reserved_amount: Decimal, settings: Settings) -> bool:
    drift = quantize_money(drift_amount)
    absolute_threshold = quantize_money(settings.drift_absolute_tolerance)
    ratio_threshold = quantize_money(settings.drift_ratio_tolerance)
    if drift <= absolute_threshold:
        return False
    reserved = quantize_money(reserved_amount)
    if reserved <= 0:
        return True
    return (drift / reserved) > ratio_threshold


def enforce_drift_on_commit(
    session: Session,
    settings: Settings,
    *,
    account_id: str,
    operation_id: str,
    crystal_id: str,
    platform: str,
    reserved: Decimal,
    committed: Decimal,
    now: datetime | None = None,
) -> dict:
    """Apply drift tolerance; lock account when committed exposure exceeds reserved beyond threshold."""
    drift_amount = quantize_money(max(Decimal("0"), committed - reserved))
    if drift_amount <= 0:
        return {"drift_enforced": False, "drift_amount": "0"}

    if not drift_exceeds_tolerance(drift_amount, reserved, settings):
        append_decision_event(
            session,
            operation_id=operation_id,
            crystal_id=crystal_id,
            account_id=account_id,
            event_type="DRIFT_TOLERATED",
            exposure_delta=Decimal("0"),
            metadata={"drift_amount": str(drift_amount)},
        )
        get_counters().increment("drift_tolerated_total")
        return {"drift_enforced": False, "drift_amount": str(drift_amount)}

    ts = now or datetime.now(timezone.utc)
    ts_param = ts.isoformat() if session.bind.dialect.name == "sqlite" else ts
    session.execute(
        text(
            """
            UPDATE account_ledgers
            SET active = FALSE,
                lock_reason = :reason,
                locked_at = :locked_at,
                updated_at = :locked_at
            WHERE account_id = :account_id AND ledger_type = 'exposure' AND currency = 'USD'
            """
        ),
        {
            "reason": "DRIFT_THRESHOLD_EXCEEDED",
            "locked_at": ts_param,
            "account_id": account_id,
        },
    )
    record_guardrail_incident(
        session,
        operation_id=operation_id,
        crystal_id=crystal_id,
        incident_type="DRIFT_THRESHOLD_EXCEEDED",
        platform=platform,
        metadata={
            "drift_amount": str(drift_amount),
            "reserved_exposure": str(quantize_money(reserved)),
            "committed_exposure": str(quantize_money(committed)),
            "threshold_absolute": str(quantize_money(settings.drift_absolute_tolerance)),
            "threshold_ratio": str(quantize_money(settings.drift_ratio_tolerance)),
        },
    )
    append_decision_event(
        session,
        operation_id=operation_id,
        crystal_id=crystal_id,
        account_id=account_id,
        event_type="DRIFT_ENFORCED",
        exposure_delta=Decimal("0"),
        metadata={"drift_amount": str(drift_amount)},
    )
    get_counters().increment("drift_enforced_total")
    return {"drift_enforced": True, "drift_amount": str(drift_amount)}
