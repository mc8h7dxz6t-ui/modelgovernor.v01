"""Regulatory ops + crystal ops invariant probes."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SIDECAR = ROOT / "spine" / "sidecar"
sys.path.insert(0, str(SIDECAR))

FG_TESTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(FG_TESTS))

from conftest_spine import spine_db  # noqa: F401

HEADERS = {"x-internal-token": "test-token"}


def test_regulatory_ops_clean_after_lifecycle(spine_db):
    from app.commit_ledger import commit_operation, crystallize_operation
    from app.config import Settings, get_settings
    from app.db import get_db_session, override_engine
    from app.regulatory_ops import assert_regulatory_ops_invariants
    from decimal import Decimal

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
            operation_id="reg-1",
            account_id="desk-default",
            risk_tier="low",
            facets={"amount": "10.00"},
            reserved_exposure=Decimal("5"),
            policy_id="wire-critical-us",
        )
    with get_db_session() as session:
        commit_operation(
            session,
            crystal_id=cr.crystal_id,
            facets={"amount": "10.00"},
            committed_exposure=Decimal("5"),
        )
    with get_db_session() as session:
        result = assert_regulatory_ops_invariants(session)
        assert result["negative_balances"] == 0
        assert result["exposure_cap_overruns"] == 0


def test_crystal_ops_detects_duplicate_commit(spine_db):
    from app.commit_ledger import append_decision_event, crystallize_operation
    from app.config import Settings
    from app.crystal_ops import CrystalOpsInvariantError, assert_crystal_ops_invariants
    from app.db import get_db_session, override_engine
    from decimal import Decimal

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
            operation_id="dup-commit",
            account_id="desk-default",
            risk_tier="low",
            facets={"amount": "1"},
        )
        commit_operation = None
    with get_db_session() as session:
        from app.commit_ledger import commit_operation as co

        co(session, crystal_id=cr.crystal_id, facets={"amount": "1"}, committed_exposure=Decimal("0"))
        append_decision_event(
            session,
            operation_id="dup-commit",
            crystal_id=cr.crystal_id,
            account_id="desk-default",
            event_type="COMMITTED_FINAL",
            exposure_delta=Decimal("0"),
            metadata={"duplicate": True},
        )
        session.commit()
    with get_db_session() as session:
        with pytest.raises(CrystalOpsInvariantError):
            assert_crystal_ops_invariants(session)
