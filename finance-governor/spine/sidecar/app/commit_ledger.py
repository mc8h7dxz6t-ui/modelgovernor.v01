from __future__ import annotations

import json
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from .config import Settings
from .currency import quantize_money
from .decision_seal import append_decision_event
from .exposure_drift import enforce_drift_on_commit
from .metrics import get_counters

# Import shared CCP from platforms/common
_FG_ROOT = Path(__file__).resolve().parents[3]
if str(_FG_ROOT) not in sys.path:
    sys.path.insert(0, str(_FG_ROOT))
from platforms.common.crystal import (  # noqa: E402
    canonical_fingerprint,
    is_horizon_expired,
    seal_crystal,
    should_strand_on_expiry,
    verify_commit_fingerprint,
)


class ConflictError(Exception):
    pass


class HorizonStrandedError(Exception):
    pass


class SurpriseCommitBlockedError(Exception):
    pass


class InsufficientExposureError(Exception):
    pass


@dataclass(frozen=True)
class CrystallizeResult:
    crystal_id: str
    operation_id: str
    status: str
    horizon_expires_at: datetime


@dataclass(frozen=True)
class CommitResult:
    operation_id: str
    crystal_id: str
    status: str


from spine_core.commit_helpers import ts_param as _ts_param, utcnow as _utcnow
from spine_core.commit_mesh import mesh_block_reason


def _money_param(value: Decimal) -> str | Decimal:
    return str(quantize_money(value))


def _check_mesh_block(session: Session, platform: str, facets: dict[str, Any]) -> None:
    reason = mesh_block_reason(session, platform, facets)
    if reason:
        get_counters().increment("crystal_mesh_block_total")
        raise SurpriseCommitBlockedError(reason)


def crystallize_operation(
    session: Session,
    settings: Settings,
    *,
    platform: str,
    operation_id: str,
    account_id: str,
    risk_tier: str,
    facets: dict[str, Any],
    policy_id: str | None = None,
    reserved_exposure: Decimal = Decimal("0"),
    parent_crystal_id: str | None = None,
) -> CrystallizeResult:
    from .platform_registry import assert_platform_allowed, validate_platform_facets

    record = assert_platform_allowed(session, platform)
    validate_platform_facets(session, platform, facets)
    if policy_id is None and record.default_policy_id:
        policy_id = record.default_policy_id

    existing = session.execute(
        text(
            """
            SELECT crystal_id, request_fingerprint, horizon_expires_at
            FROM governance_crystals WHERE platform = :p AND operation_id = :o
            """
        ),
        {"p": platform, "o": operation_id},
    ).mappings().first()
    if existing:
        fp = canonical_fingerprint(platform, operation_id, facets)
        if fp != existing["request_fingerprint"]:
            raise ConflictError("fingerprint mismatch on crystallize replay")
        get_counters().increment("crystallize_idempotent_replay_total")
        horizon = existing["horizon_expires_at"]
        if isinstance(horizon, str):
            horizon = datetime.fromisoformat(horizon.replace("Z", "+00:00"))
        return CrystallizeResult(
            crystal_id=existing["crystal_id"],
            operation_id=operation_id,
            status="REPLAY",
            horizon_expires_at=horizon,
        )

    horizon_ms = None
    if policy_id:
        pol = session.execute(
            text(
                """
                SELECT commit_horizon_ms, max_exposure_per_commit, enabled
                FROM instrument_policy_registry WHERE policy_id = :pid
                """
            ),
            {"pid": policy_id},
        ).mappings().first()
        if not pol or not pol["enabled"]:
            raise ConflictError(f"policy not enabled: {policy_id}")
        horizon_ms = int(pol["commit_horizon_ms"])
        max_exp = quantize_money(pol["max_exposure_per_commit"])
        if reserved_exposure > max_exp:
            raise ConflictError("reserved exposure exceeds policy max")

    prev_crystal_hash = session.execute(
        text("SELECT crystal_hash FROM governance_crystals ORDER BY crystallized_at DESC LIMIT 1")
    ).scalar()

    crystal = seal_crystal(
        platform=platform,
        operation_id=operation_id,
        risk_tier=risk_tier,
        facets=facets,
        prev_crystal_hash=prev_crystal_hash,
        parent_crystal_id=parent_crystal_id,
        horizon_ms=horizon_ms,
    )

    reserved = quantize_money(reserved_exposure)
    if reserved > 0:
        lock_clause = " FOR UPDATE" if session.bind.dialect.name == "postgresql" else ""
        bal = session.execute(
            text(
                f"""
                SELECT balance, active FROM account_ledgers
                WHERE account_id = :a AND ledger_type = 'exposure' AND currency = 'USD'
                {lock_clause}
                """
            ),
            {"a": account_id},
        ).mappings().first()
        if not bal or not bal["active"]:
            raise InsufficientExposureError("account not found or inactive")
        if quantize_money(bal["balance"]) < reserved:
            raise InsufficientExposureError("insufficient exposure balance")
        session.execute(
            text(
                """
                UPDATE account_ledgers SET balance = balance - :amt, updated_at = :now
                WHERE account_id = :a AND ledger_type = 'exposure' AND currency = 'USD'
                """
            ),
            {"amt": _money_param(reserved), "now": _ts_param(session, _utcnow()), "a": account_id},
        )

    expires_at = _utcnow() + timedelta(seconds=settings.commit_ttl_seconds)
    facets_json = json.dumps(facets)
    facets_sql = ":facets" if session.bind.dialect.name == "sqlite" else "CAST(:facets AS jsonb)"
    session.execute(
        text(
            f"""
            INSERT INTO governance_crystals (
                crystal_id, platform, operation_id, risk_tier, policy_id,
                facets, request_fingerprint, crystal_hash, prev_crystal_hash,
                parent_crystal_id, horizon_expires_at
            ) VALUES (
                :crystal_id, :platform, :operation_id, :risk_tier, :policy_id,
                {facets_sql}, :fp, :ch, :pch, :parent, :horizon
            )
            """
        ),
        {
            "crystal_id": crystal.crystal_id,
            "platform": platform,
            "operation_id": operation_id,
            "risk_tier": risk_tier,
            "policy_id": policy_id,
            "facets": facets_json,
            "fp": crystal.request_fingerprint,
            "ch": crystal.crystal_hash,
            "pch": crystal.prev_crystal_hash,
            "parent": parent_crystal_id,
            "horizon": _ts_param(session, crystal.horizon_expires_at),
        },
    )
    session.execute(
        text(
            """
            INSERT INTO commit_escrow_ledger (
                operation_id, crystal_id, account_id, platform,
                reserved_exposure, status, expires_at
            ) VALUES (
                :op, :cid, :acct, :plat, :res, 'CRYSTALLIZED', :exp
            )
            """
        ),
        {
            "op": operation_id,
            "cid": crystal.crystal_id,
            "acct": account_id,
            "plat": platform,
            "res": _money_param(reserved),
            "exp": _ts_param(session, expires_at),
        },
    )
    append_decision_event(
        session,
        operation_id=operation_id,
        crystal_id=crystal.crystal_id,
        account_id=account_id,
        event_type="CRYSTAL_CREATED",
        exposure_delta=-reserved,
        metadata={"platform": platform, "risk_tier": risk_tier},
    )
    session.commit()
    get_counters().increment("crystallize_success_total")
    return CrystallizeResult(
        crystal_id=crystal.crystal_id,
        operation_id=operation_id,
        status="CRYSTALLIZED",
        horizon_expires_at=crystal.horizon_expires_at,
    )


def commit_operation(
    session: Session,
    settings: Settings,
    *,
    crystal_id: str,
    facets: dict[str, Any],
    committed_exposure: Decimal = Decimal("0"),
    outcome: str = "committed",
    late_authority: bool = False,
) -> CommitResult:
    lock = "" if session.bind.dialect.name == "sqlite" else " FOR UPDATE OF c, e"
    row = session.execute(
        text(
            f"""
            SELECT c.crystal_id, c.platform, c.operation_id, c.risk_tier, c.facets,
                   c.request_fingerprint, c.horizon_expires_at, c.terminal_state,
                   e.account_id, e.status, e.reserved_exposure
            FROM governance_crystals c
            JOIN commit_escrow_ledger e ON e.crystal_id = c.crystal_id
            WHERE c.crystal_id = :cid
            {lock}
            """
        ),
        {"cid": crystal_id},
    ).mappings().first()
    if not row:
        get_counters().increment("surprise_commit_blocked_total")
        raise SurpriseCommitBlockedError("unknown crystal")

    if row["terminal_state"]:
        return CommitResult(operation_id=row["operation_id"], crystal_id=crystal_id, status="REPLAY")

    stored_facets = row["facets"] if isinstance(row["facets"], dict) else json.loads(row["facets"])
    horizon_at = row["horizon_expires_at"]
    if isinstance(horizon_at, str):
        horizon_at = datetime.fromisoformat(horizon_at.replace("Z", "+00:00"))
    from platforms.common.crystal import Crystal

    crystal = Crystal(
        crystal_id=row["crystal_id"],
        platform=row["platform"],
        operation_id=row["operation_id"],
        risk_tier=row["risk_tier"],
        facets=stored_facets,
        request_fingerprint=row["request_fingerprint"],
        crystal_hash="",
        prev_crystal_hash=None,
        parent_crystal_id=None,
        horizon_expires_at=horizon_at,
    )
    if not verify_commit_fingerprint(crystal, facets):
        get_counters().increment("crystal_fingerprint_mismatch_total")
        raise SurpriseCommitBlockedError("fingerprint mismatch")

    if is_horizon_expired(crystal) and not late_authority:
        if should_strand_on_expiry(crystal.risk_tier):
            get_counters().increment("crystal_horizon_strand_total")
            raise HorizonStrandedError("horizon expired")
        raise SurpriseCommitBlockedError("horizon expired")

    _check_mesh_block(session, row["platform"], facets)

    committed = quantize_money(committed_exposure)
    reserved = quantize_money(row["reserved_exposure"])
    refund = reserved - committed
    if refund > 0:
        session.execute(
            text(
                """
                UPDATE account_ledgers SET balance = balance + :amt, updated_at = :now
                WHERE account_id = :a AND ledger_type = 'exposure' AND currency = 'USD'
                """
            ),
            {"amt": _money_param(refund), "now": _ts_param(session, _utcnow()), "a": row["account_id"]},
        )

    now = _utcnow()
    session.execute(
        text(
            """
            UPDATE commit_escrow_ledger
            SET status = 'COMMITTED', committed_exposure = :ce, committed_at = :now
            WHERE crystal_id = :cid
            """
        ),
        {"ce": _money_param(committed), "now": _ts_param(session, now), "cid": crystal_id},
    )
    session.execute(
        text("UPDATE governance_crystals SET terminal_state = 'COMMITTED' WHERE crystal_id = :cid"),
        {"cid": crystal_id},
    )
    drift_result = enforce_drift_on_commit(
        session,
        settings,
        account_id=row["account_id"],
        operation_id=row["operation_id"],
        crystal_id=crystal_id,
        platform=row["platform"],
        reserved=reserved,
        committed=committed,
        now=now,
    )
    append_decision_event(
        session,
        operation_id=row["operation_id"],
        crystal_id=crystal_id,
        account_id=row["account_id"],
        event_type="COMMITTED_FINAL",
        exposure_delta=committed,
        metadata={"outcome": outcome, **drift_result},
    )
    session.commit()
    get_counters().increment("commit_success_total")
    return CommitResult(operation_id=row["operation_id"], crystal_id=crystal_id, status="COMMITTED")


@dataclass(frozen=True)
class AdjudicateResult:
    operation_id: str
    crystal_id: str
    status: str


def adjudicate_operation(
    session: Session,
    *,
    crystal_id: str,
    action: str,
    reason: str = "manual_adjudicate",
) -> AdjudicateResult:
    if action != "strand":
        raise SurpriseCommitBlockedError(f"unsupported adjudicate action: {action}")

    lock = "" if session.bind.dialect.name == "sqlite" else " FOR UPDATE"
    row = session.execute(
        text(
            f"""
            SELECT c.crystal_id, c.operation_id, c.terminal_state,
                   e.account_id, e.reserved_exposure, e.status
            FROM governance_crystals c
            JOIN commit_escrow_ledger e ON e.crystal_id = c.crystal_id
            WHERE c.crystal_id = :cid
            {lock}
            """
        ),
        {"cid": crystal_id},
    ).mappings().first()
    if not row:
        raise SurpriseCommitBlockedError("unknown crystal")
    if row["terminal_state"]:
        return AdjudicateResult(operation_id=row["operation_id"], crystal_id=crystal_id, status="REPLAY")

    reserved = quantize_money(row["reserved_exposure"])
    if reserved > 0:
        session.execute(
            text(
                """
                UPDATE account_ledgers SET balance = balance + :amt, updated_at = :now
                WHERE account_id = :a AND ledger_type = 'exposure' AND currency = 'USD'
                """
            ),
            {"amt": _money_param(reserved), "now": _ts_param(session, _utcnow()), "a": row["account_id"]},
        )

    session.execute(
        text("UPDATE governance_crystals SET terminal_state = 'STRANDED' WHERE crystal_id = :cid"),
        {"cid": crystal_id},
    )
    session.execute(
        text(
            """
            UPDATE commit_escrow_ledger
            SET status = 'STRANDED', terminal_reason = :reason
            WHERE crystal_id = :cid
            """
        ),
        {"cid": crystal_id, "reason": reason[:255]},
    )
    append_decision_event(
        session,
        operation_id=row["operation_id"],
        crystal_id=crystal_id,
        account_id=row["account_id"],
        event_type="STRANDED_HOLD",
        exposure_delta=Decimal("0"),
        metadata={"reason": reason, "source": "adjudicate"},
    )
    session.commit()
    get_counters().increment("crystal_manual_strand_total")
    return AdjudicateResult(operation_id=row["operation_id"], crystal_id=crystal_id, status="STRANDED")
