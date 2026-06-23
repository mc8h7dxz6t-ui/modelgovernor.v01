from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from reconciler.app.sweeper import sweep_expired_reservations
from sidecar.app.config import Settings
from sidecar.app.ledger import LedgerError, apply_settlement, reserve_operation
from sidecar.app.metrics import get_counters
from sidecar.app.schemas import ReserveRequest, SettleRequest

sqlite3.register_adapter(Decimal, lambda v: str(v))


def _settings() -> Settings:
    return Settings(
        database_url="sqlite:///:memory:",
        redis_url="redis://localhost:6379/0",
        sidecar_internal_tokens="token",
        reserve_ttl_seconds=300,
        default_trace_cap_amount=Decimal("100"),
        drift_absolute_tolerance=Decimal("0.5"),
        drift_ratio_tolerance=Decimal("0.05"),
    )


def _build_engine(tmp_path: Path) -> Engine:
    engine = create_engine(
        f"sqlite:///{tmp_path / 'phase4-anomaly.db'}",
        connect_args={"check_same_thread": False},
        future=True,
    )
    with engine.begin() as conn:
        conn.execute(text("PRAGMA journal_mode=WAL"))
        conn.execute(
            text(
                """
                CREATE TABLE user_wallets (
                    user_id TEXT PRIMARY KEY,
                    balance NUMERIC(18,6) NOT NULL DEFAULT 100.000000,
                    active BOOLEAN NOT NULL DEFAULT TRUE,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    locked_at TIMESTAMP,
                    lock_reason TEXT
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE model_policy_registry (
                    model_name TEXT PRIMARY KEY,
                    provider TEXT NOT NULL,
                    enabled BOOLEAN NOT NULL DEFAULT TRUE,
                    max_input_tokens INTEGER NOT NULL,
                    max_output_tokens INTEGER NOT NULL,
                    max_cost_per_request NUMERIC(18,6) NOT NULL,
                    stream_allowed BOOLEAN NOT NULL DEFAULT TRUE,
                    fallback_price_per_token NUMERIC(18,6) NOT NULL,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE escrow_ledger (
                    idempotency_key TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    trace_id TEXT NOT NULL,
                    model TEXT NOT NULL,
                    request_fingerprint TEXT NOT NULL,
                    reserved_amount NUMERIC(18,6) NOT NULL,
                    actual_amount NUMERIC(18,6) NOT NULL DEFAULT 0.000000,
                    status TEXT NOT NULL,
                    provider_request_id TEXT,
                    terminal_reason TEXT,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP NOT NULL,
                    settled_at TIMESTAMP,
                    expired_at TIMESTAMP,
                    reconciled BOOLEAN NOT NULL DEFAULT FALSE,
                    trace_cap_amount NUMERIC(18,6) NOT NULL DEFAULT 25.000000,
                    dispatch_started_at TIMESTAMP,
                    drift_amount NUMERIC(18,6) NOT NULL DEFAULT 0.000000
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE ledger_events (
                    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    idempotency_key TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    amount_delta NUMERIC(18,6) NOT NULL,
                    metadata TEXT NOT NULL DEFAULT '{}',
                    recorded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE trace_budget_state (
                    trace_id TEXT PRIMARY KEY,
                    cap_amount NUMERIC(18,6) NOT NULL,
                    reserved_total NUMERIC(18,6) NOT NULL DEFAULT 0.000000,
                    settled_total NUMERIC(18,6) NOT NULL DEFAULT 0.000000,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE provider_dispatch_attempts (
                    attempt_key TEXT PRIMARY KEY,
                    idempotency_key TEXT NOT NULL,
                    provider_name TEXT,
                    model_name TEXT,
                    provider_request_id TEXT UNIQUE,
                    status TEXT NOT NULL,
                    terminal_reason TEXT,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        )
    return engine


def _seed(engine: Engine, user_id: str, balance: Decimal = Decimal("100")) -> None:
    with engine.begin() as conn:
        conn.execute(
            text("INSERT INTO user_wallets (user_id, balance, active) VALUES (:uid, :bal, TRUE)"),
            {"uid": user_id, "bal": float(balance)},
        )
        conn.execute(
            text(
                """
                INSERT INTO model_policy_registry (
                    model_name, provider, enabled, max_input_tokens, max_output_tokens,
                    max_cost_per_request, stream_allowed, fallback_price_per_token
                ) VALUES ('gpt-4o-mini', 'openai', 1, 8192, 4096, 200.0, 1, 0.00001)
                """
            )
        )


def _reserve(engine: Engine, settings: Settings, *, user_id: str, key: str, cost: Decimal) -> None:
    with Session(engine) as session:
        reserve_operation(
            session,
            settings,
            ReserveRequest(
                user_id=user_id,
                trace_id=f"trace-{key}",
                idempotency_key=key,
                model="gpt-4o-mini",
                estimated_cost=cost,
                trace_cap=Decimal("500"),
            ),
        )


def test_phase4_anomaly_counters_remain_zero_on_happy_path(tmp_path: Path) -> None:
    engine = _build_engine(tmp_path)
    settings = _settings()
    get_counters().reset()
    _seed(engine, "u1", Decimal("50"))
    _reserve(engine, settings, user_id="u1", key="ok-op", cost=Decimal("10"))

    with Session(engine) as session:
        apply_settlement(
            session,
            settings,
            SettleRequest(idempotency_key="ok-op", outcome="SETTLED", actual_cost=Decimal("9.5")),
        )

    snapshot = get_counters().snapshot()
    assert snapshot["negative_wallet_detected_total"] == 0
    assert snapshot["duplicate_settlement_anomaly_total"] == 0
    assert snapshot["duplicate_refund_anomaly_total"] == 0


def test_phase4_negative_wallet_probe_triggers_counter(tmp_path: Path) -> None:
    engine = _build_engine(tmp_path)
    settings = _settings()
    get_counters().reset()
    _seed(engine, "u2", Decimal("10"))
    _reserve(engine, settings, user_id="u2", key="neg-op", cost=Decimal("5"))

    with pytest.raises(LedgerError, match="negative balance"):
        with Session(engine) as session:
            apply_settlement(
                session,
                settings,
                SettleRequest(idempotency_key="neg-op", outcome="SETTLED", actual_cost=Decimal("20")),
            )

    assert get_counters().snapshot()["negative_wallet_detected_total"] == 1


def test_phase4_duplicate_settlement_probe_triggers_counter(tmp_path: Path) -> None:
    engine = _build_engine(tmp_path)
    settings = _settings()
    get_counters().reset()
    _seed(engine, "u3", Decimal("30"))
    _reserve(engine, settings, user_id="u3", key="dup-settle-op", cost=Decimal("10"))
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO ledger_events (idempotency_key, user_id, event_type, amount_delta, metadata)
                VALUES ('dup-settle-op', 'u3', 'SETTLED_FINAL', 0, '{}')
                """
            )
        )

    with Session(engine) as session:
        apply_settlement(
            session,
            settings,
            SettleRequest(idempotency_key="dup-settle-op", outcome="SETTLED", actual_cost=Decimal("9")),
        )

    assert get_counters().snapshot()["duplicate_settlement_anomaly_total"] == 1


def test_phase4_duplicate_refund_probe_triggers_counter(tmp_path: Path) -> None:
    engine = _build_engine(tmp_path)
    settings = _settings()
    get_counters().reset()
    _seed(engine, "u4", Decimal("30"))
    _reserve(engine, settings, user_id="u4", key="dup-refund-op", cost=Decimal("4"))
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                UPDATE escrow_ledger
                SET expires_at = :expired_at
                WHERE idempotency_key = 'dup-refund-op'
                """
            ),
            {"expired_at": datetime.now(timezone.utc) - timedelta(minutes=10)},
        )
        conn.execute(
            text(
                """
                INSERT INTO ledger_events (idempotency_key, user_id, event_type, amount_delta, metadata)
                VALUES ('dup-refund-op', 'u4', 'EXPIRED_SWEEP', 0, '{}')
                """
            )
        )

    with Session(engine) as session:
        sweep_expired_reservations(session, batch_size=10)

    assert get_counters().snapshot()["duplicate_refund_anomaly_total"] == 1
