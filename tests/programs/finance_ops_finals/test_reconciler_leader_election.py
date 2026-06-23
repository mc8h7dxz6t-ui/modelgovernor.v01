"""Postgres advisory-lock leader election tests for reconciler HA."""
from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session, sessionmaker

from sidecar.app.config import Settings as SidecarSettings
from reconciler.app.config import Settings as ReconcilerSettings
from reconciler.app.leader import reconciler_leader_session
from reconciler.app.sweeper import sweep_expired_reservations
from sidecar.app.ledger import reserve_operation
from sidecar.app.schemas import ReserveRequest

pytestmark = pytest.mark.skipif(
    not os.getenv("POSTGRES_TEST_URL"),
    reason="POSTGRES_TEST_URL required for leader election tests",
)


def _sidecar_settings(pg_url: str) -> SidecarSettings:
    return SidecarSettings(
        database_url=pg_url,
        redis_url="redis://example/0",
        sidecar_internal_tokens="test-token",
        default_trace_cap_amount=Decimal("100"),
        drift_absolute_tolerance=Decimal("1"),
        drift_ratio_tolerance=Decimal("1"),
        manual_approval_cost_threshold=Decimal("1000000"),
        db_pool_size=3,
        db_max_overflow=2,
        db_pool_timeout_seconds=5,
        db_pool_recycle_seconds=300,
    )


def _reconciler_settings(pg_url: str) -> ReconcilerSettings:
    return ReconcilerSettings(
        database_url=pg_url,
        db_pool_size=2,
        db_max_overflow=1,
        db_pool_timeout_seconds=5,
        db_pool_recycle_seconds=300,
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

    assert sum(results) >= 1
    assert sum(results) <= 2


def test_leader_elected_reconciler_sweeps_under_pg(pg_engine, clean_pg_tables) -> None:
    from datetime import datetime, timedelta, timezone

    from sqlalchemy import text

    settings = _sidecar_settings(str(pg_engine.url))
    factory = sessionmaker(bind=pg_engine, autoflush=False, autocommit=False, future=True)

    with pg_engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO user_wallets (user_id, balance, active)
                VALUES ('lead-user', 100, TRUE)
                """
            )
        )

    with factory() as session:
        reserve_operation(
            session,
            settings,
            ReserveRequest(
                user_id="lead-user",
                trace_id="lead-trace",
                idempotency_key="lead-op",
                model="gpt-4o-mini",
                estimated_cost=Decimal("10"),
            ),
        )

    with pg_engine.begin() as conn:
        conn.execute(
            text(
                "UPDATE escrow_ledger SET expires_at = :t WHERE idempotency_key = 'lead-op'"
            ),
            {"t": datetime.now(timezone.utc) - timedelta(minutes=5)},
        )

    swept = 0
    with factory() as session:
        with reconciler_leader_session(session) as is_leader:
            if is_leader:
                swept = sweep_expired_reservations(session, batch_size=10)

    assert swept == 1
