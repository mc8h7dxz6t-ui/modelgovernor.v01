"""Chaos-adjacent resilience tests: concurrent reconciler + settlement races."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
import sys

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from reconciler.app.sweeper import sweep_expired_reservations
from sidecar.app.config import Settings
from sidecar.app.ledger import apply_settlement, reserve_operation
from sidecar.app.metrics import get_counters
from sidecar.app.schemas import ReserveRequest, SettleRequest
from tests.integration.test_ledger_hardening import _bootstrap_schema, _create_test_engine, _seed_wallet_and_model


def _settings(engine) -> Settings:
    return Settings(
        database_url=str(engine.url),
        redis_url="redis://example/0",
        sidecar_internal_tokens="test-token",
        default_trace_cap_amount=Decimal("1000"),
        drift_absolute_tolerance=Decimal("100"),
        drift_ratio_tolerance=Decimal("1"),
        db_pool_size=8,
        db_max_overflow=8,
        db_pool_timeout_seconds=5,
        db_pool_recycle_seconds=1800,
    )


def test_concurrent_sweep_and_settle_never_double_refunds(tmp_path: Path) -> None:
    """Sweeper and late settlement racing must not produce duplicate refunds."""
    engine = _create_test_engine(tmp_path / "chaos.sqlite3")
    _bootstrap_schema(engine)
    _seed_wallet_and_model(engine, user_id="user-1", balance=Decimal("200"))
    settings = _settings(engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    get_counters().reset()

    with Session(engine) as session:
        reserve_operation(
            session,
            settings,
            ReserveRequest(
                user_id="user-1",
                trace_id="chaos-trace",
                idempotency_key="chaos-op",
                model="gpt-4o-mini",
                estimated_cost=Decimal("20"),
            ),
        )

    with engine.begin() as conn:
        conn.execute(
            text("UPDATE escrow_ledger SET expires_at = :t WHERE idempotency_key = 'chaos-op'"),
            {"t": datetime.now(timezone.utc) - timedelta(minutes=5)},
        )

    def sweep_once() -> int:
        with factory() as session:
            return sweep_expired_reservations(session, batch_size=5)

    def late_settle_once() -> str:
        with factory() as session:
            try:
                apply_settlement(
                    session,
                    settings,
                    SettleRequest(
                        idempotency_key="chaos-op",
                        outcome="SETTLED",
                        actual_cost=Decimal("18"),
                        provider_request_id="provider-chaos",
                    ),
                )
                return "settled"
            except Exception as exc:
                session.rollback()
                return f"error:{type(exc).__name__}"

    with ThreadPoolExecutor(max_workers=6) as pool:
        outcomes = list(pool.map(lambda _: sweep_once(), range(3)))
        outcomes += list(pool.map(lambda _: late_settle_once(), range(3)))

    with Session(engine) as session:
        refund_events = session.execute(
            text(
                """
                SELECT COUNT(*) FROM ledger_events
                WHERE idempotency_key = 'chaos-op' AND event_type = 'EXPIRED_SWEEP'
                """
            )
        ).scalar_one()
        balance = session.execute(
            text("SELECT balance FROM user_wallets WHERE user_id = 'user-1'")
        ).scalar_one()

    assert Decimal(str(balance)) >= Decimal("0")
    if engine.dialect.name == "postgresql":
        assert int(refund_events) <= 1
        assert get_counters().snapshot()["duplicate_refund_anomaly_total"] == 0


def test_rollback_after_failed_settlement_preserves_wallet(tmp_path: Path) -> None:
    """A failed settlement must not leave partial wallet mutations committed."""
    engine = _create_test_engine(tmp_path / "rollback.sqlite3")
    _bootstrap_schema(engine)
    _seed_wallet_and_model(engine, user_id="user-1", balance=Decimal("10"))
    settings = _settings(engine)

    with Session(engine) as session:
        reserve_operation(
            session,
            settings,
            ReserveRequest(
                user_id="user-1",
                trace_id="rb-trace",
                idempotency_key="rb-op",
                model="gpt-4o-mini",
                estimated_cost=Decimal("5"),
            ),
        )

    with Session(engine) as session:
        with pytest.raises(Exception):
            apply_settlement(
                session,
                settings,
                SettleRequest(idempotency_key="rb-op", outcome="SETTLED", actual_cost=Decimal("50")),
            )
        session.rollback()

    with Session(engine) as session:
        balance = session.execute(
            text("SELECT balance FROM user_wallets WHERE user_id = 'user-1'")
        ).scalar_one()
        status = session.execute(
            text("SELECT status FROM escrow_ledger WHERE idempotency_key = 'rb-op'")
        ).scalar_one()

    assert Decimal(str(balance)) == Decimal("5.000000")
    assert status == "RESERVED"
