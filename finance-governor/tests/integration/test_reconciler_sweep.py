"""Reconciler horizon sweep with hash-chained events."""
from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[2]
SIDECAR = ROOT / "spine" / "sidecar"
RECON = ROOT / "spine" / "reconciler"
sys.path.insert(0, str(SIDECAR))
sys.path.insert(0, str(RECON))

FG_TESTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(FG_TESTS))

from conftest_spine import spine_db  # noqa: F401


def test_sweep_strands_high_risk_and_preserves_chain(spine_db):
    from app.commit_ledger import crystallize_operation
    from app.config import Settings
    from app.db import get_db_session, override_engine
    from app.decision_chain_verify import verify_decision_chain

    settings = Settings(
        database_url="sqlite+pysqlite:///:memory:",
        redis_url="redis://localhost:6380/0",
        fg_internal_tokens="test-token",
    )
    override_engine(spine_db)

    with get_db_session() as session:
        cr = crystallize_operation(
            session,
            settings,
            platform="wire_match",
            operation_id="sweep-1",
            account_id="desk-default",
            risk_tier="critical",
            facets={"amount": "100"},
            policy_id="wire-critical-us",
        )
        past = "1970-01-01 00:00:00"
        session.execute(
            text("UPDATE governance_crystals SET horizon_expires_at = :p WHERE crystal_id = :c"),
            {"p": past, "c": cr.crystal_id},
        )
        session.commit()

    from importlib.util import spec_from_file_location, module_from_spec

    spec = spec_from_file_location(
        "fg_horizon_sweeper",
        ROOT / "spine" / "reconciler" / "app" / "horizon_sweeper.py",
    )
    hs = module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(hs)

    with get_db_session() as session:
        swept = hs.sweep_expired_horizons(session)
        assert swept >= 1

    with get_db_session() as session:
        state = session.execute(
            text("SELECT terminal_state FROM governance_crystals WHERE crystal_id = :c"),
            {"c": cr.crystal_id},
        ).scalar_one()
        assert state == "STRANDED"
        chain = verify_decision_chain(session)
        assert chain.valid is True
        assert chain.sealed_count >= 2
