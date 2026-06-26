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
from .event_ledger import append_security_event
from .metrics import get_counters

# Import shared CCP from platforms/common
_CG_ROOT = Path(__file__).resolve().parents[3]
if str(_CG_ROOT) not in sys.path:
    sys.path.insert(0, str(_CG_ROOT))
from platforms.common.threat_crystal import (  # noqa: E402
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


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _money_param(value: Decimal) -> str | Decimal:
    q = quantize_money(value)
    return str(q)


def _ts_param(session: Session, value: datetime) -> str | datetime:
    if session.bind.dialect.name == "sqlite":
        return value.isoformat()
    return value


def _append_event(
    session: Session,
    *,
    operation_id: str,
    crystal_id: str | None,
    account_id: str,
    event_type: str,
    exposure_delta: Decimal,
    metadata: dict[str, Any],
) -> None:
    append_security_event(
        session,
        operation_id=operation_id,
        crystal_id=crystal_id,
        account_id=account_id,
        event_type=event_type,
        exposure_delta=exposure_delta,
        metadata=metadata,
    )


def _check_mesh_block(session: Session, platform: str, facets: dict[str, Any]) -> None:
    rows = session.execute(
        text(
            """
            SELECT parent_platform, parent_facet_key, parent_facet_value
            FROM threat_mesh_rules
            WHERE child_platform = :platform AND block_commit = TRUE AND enabled = TRUE
            """
        ),
        {"platform": platform},
    ).mappings().all()
    for rule in rows:
        parent = session.execute(
            text(
                """
                SELECT facets FROM threat_crystals
                WHERE platform = :pp AND terminal_state IS NULL
                ORDER BY crystallized_at DESC LIMIT 1
                """
            ),
            {"pp": rule["parent_platform"]},
        ).first()
        if not parent:
            continue
        pf = parent[0] if isinstance(parent[0], dict) else json.loads(parent[0])
        if pf.get(rule["parent_facet_key"]) == rule["parent_facet_value"]:
            get_counters().increment("threat_mesh_block_total")
            raise SurpriseCommitBlockedError(
                f"mesh block: {rule['parent_platform']}.{rule['parent_facet_key']}={rule['parent_facet_value']}"
            )


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
    existing = session.execute(
        text(
            "SELECT crystal_id, terminal_state FROM threat_crystals WHERE platform = :p AND operation_id = :o"
        ),
        {"p": platform, "o": operation_id},
    ).first()
    if existing:
        get_counters().increment("crystallize_success_total")
        cid = existing[0]
        horizon = session.execute(
            text("SELECT horizon_expires_at FROM threat_crystals WHERE crystal_id = :c"),
            {"c": cid},
        ).scalar_one()
        return CrystallizeResult(crystal_id=cid, operation_id=operation_id, status="REPLAY", horizon_expires_at=horizon)

    horizon_ms = None
    if policy_id:
        pol = session.execute(
            text(
                """
                SELECT commit_horizon_ms, max_exposure_per_commit, enabled
                FROM control_policy_registry WHERE policy_id = :pid
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
        text("SELECT crystal_hash FROM threat_crystals ORDER BY crystallized_at DESC LIMIT 1")
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
                SELECT balance, active FROM principal_budgets
                WHERE account_id = :a AND ledger_type = 'action_budget' AND currency = 'USD'
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
                UPDATE principal_budgets SET balance = balance - :amt, updated_at = :now
                WHERE account_id = :a AND ledger_type = 'action_budget' AND currency = 'USD'
                """
            ),
            {"amt": _money_param(reserved), "now": _ts_param(session, _utcnow()), "a": account_id},
        )

    expires_at = _utcnow() + timedelta(seconds=settings.commit_ttl_seconds)
    facets_json = json.dumps(facets)
    facets_sql = ":facets" if session.bind.dialect.name == "sqlite" else ":facets::jsonb"
    session.execute(
        text(
            f"""
            INSERT INTO threat_crystals (
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
            INSERT INTO action_escrow_ledger (
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
    _append_event(
        session,
        operation_id=operation_id,
        crystal_id=crystal.crystal_id,
        account_id=account_id,
        event_type="THREAT_CRYSTAL_CREATED",
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
            FROM threat_crystals c
            JOIN action_escrow_ledger e ON e.crystal_id = c.crystal_id
            WHERE c.crystal_id = :cid
            {lock}
            """
        ),
        {"cid": crystal_id},
    ).mappings().first()
    if not row:
        get_counters().increment("surprise_authorize_blocked_total")
        raise SurpriseCommitBlockedError("unknown crystal")

    if row["terminal_state"]:
        return CommitResult(operation_id=row["operation_id"], crystal_id=crystal_id, status="REPLAY")

    stored_facets = row["facets"] if isinstance(row["facets"], dict) else json.loads(row["facets"])
    horizon_at = row["horizon_expires_at"]
    if isinstance(horizon_at, str):
        horizon_at = datetime.fromisoformat(horizon_at.replace("Z", "+00:00"))
    from platforms.common.threat_crystal import Crystal

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
        get_counters().increment("threat_fingerprint_mismatch_total")
        raise SurpriseCommitBlockedError("fingerprint mismatch")

    if is_horizon_expired(crystal) and not late_authority:
        if should_strand_on_expiry(crystal.risk_tier):
            get_counters().increment("threat_horizon_strand_total")
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
                UPDATE principal_budgets SET balance = balance + :amt, updated_at = :now
                WHERE account_id = :a AND ledger_type = 'action_budget' AND currency = 'USD'
                """
            ),
            {"amt": _money_param(refund), "now": _ts_param(session, _utcnow()), "a": row["account_id"]},
        )

    now = _utcnow()
    session.execute(
        text(
            """
            UPDATE action_escrow_ledger
            SET status = 'COMMITTED', committed_exposure = :ce, committed_at = :now
            WHERE crystal_id = :cid
            """
        ),
        {"ce": _money_param(committed), "now": _ts_param(session, now), "cid": crystal_id},
    )
    session.execute(
        text("UPDATE threat_crystals SET terminal_state = 'COMMITTED' WHERE crystal_id = :cid"),
        {"cid": crystal_id},
    )
    _append_event(
        session,
        operation_id=row["operation_id"],
        crystal_id=crystal_id,
        account_id=row["account_id"],
        event_type="COMMITTED_FINAL",
        exposure_delta=committed,
        metadata={"outcome": outcome},
    )
    session.commit()
    get_counters().increment("commit_success_total")
    return CommitResult(operation_id=row["operation_id"], crystal_id=crystal_id, status="COMMITTED")
