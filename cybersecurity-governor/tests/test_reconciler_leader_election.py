"""Postgres advisory-lock leader election tests for IG reconciler HA."""
from __future__ import annotations

import importlib.util
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

ROOT = Path(__file__).resolve().parents[1]
SIDECAR = ROOT / "spine" / "sidecar"
if str(SIDECAR) not in sys.path:
    sys.path.insert(0, str(SIDECAR))


def _load_reconciler_module(name: str):
    path = ROOT / "spine" / "reconciler" / "app" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"cg_reconciler_{name}", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


_leader = _load_reconciler_module("leader")
_sweeper = _load_reconciler_module("horizon_sweeper")
reconciler_leader_session = _leader.reconciler_leader_session
sweep_expired_horizons = _sweeper.sweep_expired_horizons

from app.commit_ledger import crystallize_operation
from app.config import Settings
from support.cyber_fixtures import EGRESS_PLATFORM, EGRESS_POLICY, egress_facets

pytestmark = pytest.mark.skipif(
    not os.getenv("POSTGRES_TEST_URL"),
    reason="POSTGRES_TEST_URL required",
)


def _settings(pg_url: str) -> Settings:
    return Settings(
        database_url=pg_url,
        redis_url="redis://example/0",
        cg_internal_tokens="test-token",
        guardrails_enabled=False,
    )


def test_only_one_reconciler_leader_acquires_lock_at_a_time(pg_engine, clean_pg_tables) -> None:
    factory = sessionmaker(bind=pg_engine, autoflush=False, autocommit=False, future=True)
    leaders: list[bool] = []

    def attempt() -> bool:
        with factory() as session:
            with reconciler_leader_session(session) as is_leader:
                if is_leader:
                    import time

                    time.sleep(0.2)
                leaders.append(is_leader)
                return is_leader

    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda _: attempt(), range(4)))

    assert sum(results) == 1


def test_leader_elected_reconciler_sweeps_horizon_under_pg(pg_engine, clean_pg_tables) -> None:
    settings = _settings(str(pg_engine.url))
    factory = sessionmaker(bind=pg_engine, autoflush=False, autocommit=False, future=True)
    facets = egress_facets(flow_id="lead-sweep-1")

    with factory() as session:
        crystallize_operation(
            session,
            settings,
            platform=EGRESS_PLATFORM,
            operation_id="lead-sweep-1",
            account_id="tenant-default",
            risk_tier="critical",
            facets=facets,
            policy_id=EGRESS_POLICY,
            reserved_budget=Decimal("0"),
        )

    with pg_engine.begin() as conn:
        conn.execute(
            text(
                """
                UPDATE governance_crystals
                SET horizon_expires_at = :t
                WHERE operation_id = 'lead-sweep-1'
                """
            ),
            {"t": datetime.now(timezone.utc) - timedelta(minutes=5)},
        )

    swept = 0
    with factory() as session:
        with reconciler_leader_session(session) as is_leader:
            if is_leader:
                swept = sweep_expired_horizons(session)

    assert swept == 1
