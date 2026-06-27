"""Postgres vigorous tests for Cybersecurity Governor spine."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text

ROOT = Path(__file__).resolve().parents[1]
SIDECAR = ROOT / "spine" / "sidecar"
TESTS = ROOT / "tests"
sys.path.insert(0, str(SIDECAR))
sys.path.insert(0, str(TESTS))

from support.cg_migrations import apply_cg_migrations

from support.cyber_fixtures import EGRESS_PLATFORM, EGRESS_POLICY, egress_facets


def _apply_migrations(engine) -> None:
    apply_cg_migrations(engine)


@pytest.fixture()
def pg_spine(monkeypatch):
    url = os.getenv("POSTGRES_TEST_URL")
    if not url:
        pytest.skip("POSTGRES_TEST_URL not set")
    engine = create_engine(url, future=True)
    _apply_migrations(engine)

    from app.config import Settings, override_settings
    from app.db import override_engine

    settings = Settings(
        database_url=url,
        redis_url="redis://localhost:6381/0",
        cg_internal_tokens="test-token",
        guardrails_enabled=False,
    )
    override_settings(settings)
    override_engine(engine)
    monkeypatch.setattr("app.config.get_settings", lambda: settings)
    yield engine
    engine.dispose()


def test_crystallize_idempotency_postgres(pg_spine):
    from decimal import Decimal

    from app.commit_ledger import crystallize_operation
    from app.config import get_settings
    from app.db import get_db_session

    facets = egress_facets(flow_id="pg-1")
    settings = get_settings()
    with get_db_session() as session:
        r1 = crystallize_operation(
            session,
            settings,
            platform=EGRESS_PLATFORM,
            operation_id="pg-idem-1",
            account_id="tenant-default",
            risk_tier="high",
            facets=facets,
            reserved_budget=Decimal("0"),
        )
        r2 = crystallize_operation(
            session,
            settings,
            platform=EGRESS_PLATFORM,
            operation_id="pg-idem-1",
            account_id="tenant-default",
            risk_tier="high",
            facets=facets,
            reserved_budget=Decimal("0"),
        )
    assert r1.crystal_id == r2.crystal_id
    assert r2.status == "REPLAY"


def test_full_lifecycle_commit_postgres(pg_spine):
    from decimal import Decimal

    from app.security_ops import assert_security_ops_invariants
    from app.commit_ledger import commit_operation, crystallize_operation
    from app.config import get_settings
    from app.db import get_db_session

    facets = egress_facets(flow_id="pg-life-1")
    settings = get_settings()
    with get_db_session() as session:
        crystal = crystallize_operation(
            session,
            settings,
            platform=EGRESS_PLATFORM,
            operation_id="pg-life-1",
            account_id="tenant-default",
            risk_tier="high",
            facets=facets,
            policy_id=EGRESS_POLICY,
            reserved_budget=Decimal("0"),
        )
    with get_db_session() as session:
        result = commit_operation(
            session,
            crystal_id=crystal.crystal_id,
            facets=facets,
            committed_budget=Decimal("0"),
            outcome="allowed",
        )
        assert result.status == "COMMITTED"
        assert_security_ops_invariants(session)


def test_insufficient_reserve_postgres(pg_spine):
    from decimal import Decimal

    import pytest
    from sqlalchemy import text

    from app.commit_ledger import InsufficientReserveError, crystallize_operation
    from app.config import get_settings
    from app.db import get_db_session

    facets = egress_facets(flow_id="pg-broke")
    settings = get_settings()
    with get_db_session() as session:
        session.execute(
            text(
                """
                UPDATE security_budget_ledgers SET balance = 10
                WHERE account_id = 'tenant-default' AND ledger_type = 'case' AND currency = 'USD'
                """
            )
        )
        session.commit()
    with pytest.raises(InsufficientReserveError):
        with get_db_session() as session:
            crystallize_operation(
                session,
                settings,
                platform=EGRESS_PLATFORM,
                operation_id="pg-broke",
                account_id="tenant-default",
                risk_tier="high",
                facets=facets,
                policy_id=EGRESS_POLICY,
                reserved_budget=Decimal("100"),
            )


def test_security_chain_verify_postgres(pg_spine):
    from decimal import Decimal

    from app.security_seal import verify_security_chain
    from app.commit_ledger import crystallize_operation
    from app.config import get_settings
    from app.db import get_db_session

    facets = egress_facets(flow_id="pg-chain")
    settings = get_settings()
    with get_db_session() as session:
        crystallize_operation(
            session,
            settings,
            platform=EGRESS_PLATFORM,
            operation_id="pg-chain",
            account_id="tenant-default",
            risk_tier="high",
            facets=facets,
            reserved_budget=Decimal("0"),
        )
    with get_db_session() as session:
        result = verify_security_chain(session)
        assert result.valid is True
        assert result.total_events >= 1
