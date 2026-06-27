"""Postgres vigorous tests for Insurance Governor spine."""
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

from support.ig_migrations import apply_ig_migrations


def _apply_migrations(engine) -> None:
    apply_ig_migrations(engine)


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
        ig_internal_tokens="test-token",
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

    facets = {"claim_id": "pg-1", "payout_amount": "100.00"}
    settings = get_settings()
    with get_db_session() as session:
        r1 = crystallize_operation(
            session,
            settings,
            platform="claim_gate",
            operation_id="pg-idem-1",
            account_id="carrier-default",
            risk_tier="high",
            facets=facets,
            reserved_reserve=Decimal("0"),
        )
        r2 = crystallize_operation(
            session,
            settings,
            platform="claim_gate",
            operation_id="pg-idem-1",
            account_id="carrier-default",
            risk_tier="high",
            facets=facets,
            reserved_reserve=Decimal("0"),
        )
    assert r1.crystal_id == r2.crystal_id
    assert r2.status == "REPLAY"


def test_full_lifecycle_commit_postgres(pg_spine):
    from decimal import Decimal

    from app.claim_ops import assert_claim_ops_invariants
    from app.commit_ledger import commit_operation, crystallize_operation
    from app.config import get_settings
    from app.db import get_db_session

    facets = {"claim_id": "pg-life-1", "payout_amount": "1000.00"}
    settings = get_settings()
    with get_db_session() as session:
        crystal = crystallize_operation(
            session,
            settings,
            platform="claim_gate",
            operation_id="pg-life-1",
            account_id="carrier-default",
            risk_tier="high",
            facets=facets,
            policy_id="claim-high-us",
            reserved_reserve=Decimal("1000"),
        )
    with get_db_session() as session:
        result = commit_operation(
            session,
            crystal_id=crystal.crystal_id,
            facets=facets,
            committed_reserve=Decimal("1000"),
            outcome="paid",
        )
        assert result.status == "COMMITTED"
        assert_claim_ops_invariants(session)


def test_insufficient_reserve_postgres(pg_spine):
    from decimal import Decimal

    import pytest

    from app.commit_ledger import InsufficientReserveError, crystallize_operation
    from app.config import get_settings
    from app.db import get_db_session

    facets = {"claim_id": "pg-broke", "payout_amount": "1.00"}
    settings = get_settings()
    with pytest.raises(InsufficientReserveError):
        with get_db_session() as session:
            crystallize_operation(
                session,
                settings,
                platform="claim_gate",
                operation_id="pg-broke",
                account_id="carrier-default",
                risk_tier="high",
                facets=facets,
                policy_id="claim-high-us",
                reserved_reserve=Decimal("99999999999"),
            )


def test_claim_chain_verify_postgres(pg_spine):
    from decimal import Decimal

    from app.claim_seal import verify_claim_chain
    from app.commit_ledger import crystallize_operation
    from app.config import get_settings
    from app.db import get_db_session

    facets = {"claim_id": "pg-chain", "payout_amount": "50.00"}
    settings = get_settings()
    with get_db_session() as session:
        crystallize_operation(
            session,
            settings,
            platform="claim_gate",
            operation_id="pg-chain",
            account_id="carrier-default",
            risk_tier="high",
            facets=facets,
            reserved_reserve=Decimal("0"),
        )
    with get_db_session() as session:
        result = verify_claim_chain(session)
        assert result["valid"] is True
        assert result["total_events"] >= 1
