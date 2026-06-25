"""Reconciler horizon sweeper — strand vs expire semantics."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

ROOT = Path(__file__).resolve().parents[1]
RECONCILER = ROOT / "spine" / "reconciler"
if str(RECONCILER) not in sys.path:
    sys.path.insert(0, str(RECONCILER))

from tests.conftest_spine import spine_db  # noqa: F401
from tests.support.reconciler_loader import load_reconciler_module


def _past_horizon() -> str:
  ts = datetime.now(timezone.utc) - timedelta(hours=1)
  return ts.strftime("%Y-%m-%d %H:%M:%S")


def _seed_crystal(session: Session, *, crystal_id: str, operation_id: str, risk_tier: str) -> None:
    session.execute(
        text(
            """
            INSERT INTO governance_crystals (
                crystal_id, platform, operation_id, risk_tier, facets,
                request_fingerprint, crystal_hash, horizon_expires_at
            ) VALUES (
                :cid, 'wire_match', :op, :tier, :facets, 'fp', 'ch', :horizon
            )
            """
        ),
        {
            "cid": crystal_id,
            "op": operation_id,
            "tier": risk_tier,
            "facets": json.dumps({"amount": "1.00"}),
            "horizon": _past_horizon(),
        },
    )
    session.execute(
        text(
            """
            INSERT INTO commit_escrow_ledger (
                operation_id, crystal_id, account_id, platform,
                reserved_exposure, status, expires_at
            ) VALUES (
                :op, :cid, 'desk-default', 'wire_match', 10.0, 'CRYSTALLIZED', :horizon
            )
            """
        ),
        {"op": operation_id, "cid": crystal_id, "horizon": _past_horizon()},
    )


def test_high_risk_horizon_strands(spine_db):
    sweep_expired_horizons = load_reconciler_module("horizon_sweeper").sweep_expired_horizons

    factory = sessionmaker(bind=spine_db)
    with factory() as session:
        _seed_crystal(session, crystal_id="c-strand", operation_id="op-strand", risk_tier="critical")
        session.commit()

    with factory() as session:
        swept = sweep_expired_horizons(session, batch_size=10)
        assert swept == 1
        terminal = session.execute(
            text("SELECT terminal_state FROM governance_crystals WHERE crystal_id = 'c-strand'")
        ).scalar_one()
        assert terminal == "STRANDED"
        status = session.execute(
            text("SELECT status FROM commit_escrow_ledger WHERE crystal_id = 'c-strand'")
        ).scalar_one()
        assert status == "STRANDED"


def test_standard_risk_horizon_expires(spine_db):
    sweep_expired_horizons = load_reconciler_module("horizon_sweeper").sweep_expired_horizons

    factory = sessionmaker(bind=spine_db)
    with factory() as session:
        _seed_crystal(session, crystal_id="c-expire", operation_id="op-expire", risk_tier="standard")
        session.commit()

    with factory() as session:
        swept = sweep_expired_horizons(session, batch_size=10)
        assert swept == 1
        terminal = session.execute(
            text("SELECT terminal_state FROM governance_crystals WHERE crystal_id = 'c-expire'")
        ).scalar_one()
        assert terminal == "EXPIRED"


def test_should_strand_on_expiry_ccp_rule():
    from platforms.common.crystal import should_strand_on_expiry

    assert should_strand_on_expiry("critical") is True
    assert should_strand_on_expiry("high") is True
    assert should_strand_on_expiry("standard") is False


def test_in_flight_horizon_strands(spine_db):
    sweep_expired_horizons = load_reconciler_module("horizon_sweeper").sweep_expired_horizons

    factory = sessionmaker(bind=spine_db)
    with factory() as session:
        _seed_crystal(session, crystal_id="c-inflight", operation_id="op-inflight", risk_tier="high")
        session.execute(
            text("UPDATE commit_escrow_ledger SET status = 'IN_FLIGHT' WHERE crystal_id = 'c-inflight'")
        )
        session.commit()

    with factory() as session:
        swept = sweep_expired_horizons(session, batch_size=10)
        assert swept == 1
        terminal = session.execute(
            text("SELECT terminal_state FROM governance_crystals WHERE crystal_id = 'c-inflight'")
        ).scalar_one()
        assert terminal == "STRANDED"
