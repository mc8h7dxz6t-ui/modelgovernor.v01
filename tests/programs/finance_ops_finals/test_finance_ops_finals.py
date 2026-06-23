"""AI Finance Ops Finals for LLMs — institutional++ program test suite."""
from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from reconciler.app.sweeper import sweep_expired_reservations
from sidecar.app.config import Settings
from sidecar.app.finance_ops import FinanceOpsInvariantError, assert_finance_ops_invariants
from sidecar.app.ledger import apply_settlement, reserve_operation
from sidecar.app.metrics import get_counters
from sidecar.app.schemas import ReserveRequest, SettleRequest
from tests.integration.test_ledger_hardening import (
    _bootstrap_schema,
    _create_test_engine,
    _seed_wallet_and_model,
)


def _settings(engine) -> Settings:
    return Settings(
        database_url=str(engine.url),
        redis_url="redis://example/0",
        sidecar_internal_tokens="test-token",
        default_trace_cap_amount=Decimal("100"),
        drift_absolute_tolerance=Decimal("0.5"),
        drift_ratio_tolerance=Decimal("0.05"),
        db_pool_size=4,
        db_max_overflow=4,
        db_pool_timeout_seconds=5,
        db_pool_recycle_seconds=1800,
    )


def test_finance_ops_final_settlement_chain_passes_invariants(tmp_path: Path) -> None:
    engine = _create_test_engine(tmp_path / "finance-finals.sqlite3")
    _bootstrap_schema(engine)
    _seed_wallet_and_model(engine, user_id="fin-user")
    settings = _settings(engine)
    get_counters().reset()

    with Session(engine) as session:
        reserve_operation(
            session,
            settings,
            ReserveRequest(
                user_id="fin-user",
                trace_id="fin-trace",
                idempotency_key="fin-op",
                model="gpt-4o-mini",
                estimated_cost=Decimal("10"),
            ),
        )
        apply_settlement(
            session,
            settings,
            SettleRequest(idempotency_key="fin-op", outcome="SETTLED", actual_cost=Decimal("9")),
        )

    with Session(engine) as session:
        assert_finance_ops_invariants(session)

    snapshot = get_counters().snapshot()
    assert snapshot["negative_wallet_detected_total"] == 0
    assert snapshot["duplicate_settlement_anomaly_total"] == 0


def test_finance_ops_final_reconciler_sweep_preserves_invariants(tmp_path: Path) -> None:
    from datetime import datetime, timedelta, timezone

    from sqlalchemy import text

    engine = _create_test_engine(tmp_path / "finance-sweep.sqlite3")
    _bootstrap_schema(engine)
    _seed_wallet_and_model(engine, user_id="fin-user")
    settings = _settings(engine)

    with Session(engine) as session:
        reserve_operation(
            session,
            settings,
            ReserveRequest(
                user_id="fin-user",
                trace_id="sweep-trace",
                idempotency_key="sweep-op",
                model="gpt-4o-mini",
                estimated_cost=Decimal("5"),
            ),
        )

    with engine.begin() as conn:
        conn.execute(
            text("UPDATE escrow_ledger SET expires_at = :t WHERE idempotency_key = 'sweep-op'"),
            {"t": datetime.now(timezone.utc) - timedelta(minutes=5)},
        )

    with Session(engine) as session:
        sweep_expired_reservations(session, batch_size=10)

    with Session(engine) as session:
        assert_finance_ops_invariants(session)


def test_finance_ops_final_negative_settlement_raises(tmp_path: Path) -> None:
    engine = _create_test_engine(tmp_path / "finance-neg.sqlite3")
    _bootstrap_schema(engine)
    _seed_wallet_and_model(engine, user_id="fin-user", balance=Decimal("10"))
    settings = _settings(engine)

    with Session(engine) as session:
        reserve_operation(
            session,
            settings,
            ReserveRequest(
                user_id="fin-user",
                trace_id="neg-trace",
                idempotency_key="neg-op",
                model="gpt-4o-mini",
                estimated_cost=Decimal("5"),
            ),
        )

    with pytest.raises(Exception):
        with Session(engine) as session:
            apply_settlement(
                session,
                settings,
                SettleRequest(idempotency_key="neg-op", outcome="SETTLED", actual_cost=Decimal("50")),
            )

    assert get_counters().snapshot()["negative_wallet_detected_total"] >= 1
