from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from sidecar.app.config import get_settings
from sidecar.app.db import override_engine
from sidecar.app.ledger import apply_settlement, reserve_operation
from sidecar.app.main import app
from sidecar.app.schemas import ReserveRequest, SettleRequest

sqlite3.register_adapter(Decimal, lambda v: str(v))


def _build_engine(tmp_path: Path) -> Engine:
    engine = create_engine(
        f"sqlite:///{tmp_path / 'phase4-reporting.db'}",
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
        conn.execute(
            text(
                """
                CREATE TABLE admin_audit_log (
                    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    admin_user_id TEXT NOT NULL,
                    action_type TEXT NOT NULL,
                    subject_key TEXT NOT NULL,
                    wallet_id TEXT,
                    operation_id TEXT,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    event_type TEXT,
                    details TEXT NOT NULL DEFAULT '{}',
                    applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        )
    return engine


def _seed(engine: Engine) -> None:
    with engine.begin() as conn:
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
        conn.execute(text("INSERT INTO user_wallets (user_id, balance, active) VALUES ('w1', 100, TRUE)"))
        conn.execute(text("INSERT INTO user_wallets (user_id, balance, active) VALUES ('w2', 80, TRUE)"))


def _headers() -> dict[str, str]:
    return {"X-Internal-Token": "test-token"}


def _reserve_and_settle(engine: Engine, key: str, wallet: str, amount: Decimal, model: str = "gpt-4o-mini") -> None:
    settings = get_settings()
    with Session(engine) as session:
        reserve_operation(
            session,
            settings,
            ReserveRequest(
                user_id=wallet,
                trace_id=f"trace-{key}",
                idempotency_key=key,
                model=model,
                estimated_cost=amount,
                trace_cap=Decimal("500"),
            ),
        )
    with Session(engine) as session:
        apply_settlement(
            session,
            settings,
            SettleRequest(idempotency_key=key, outcome="SETTLED", actual_cost=amount),
        )


def test_phase4_audit_log_endpoint_pagination_filters_and_date_bounds(
    tmp_path: Path, monkeypatch
) -> None:
    engine = _build_engine(tmp_path)
    _seed(engine)
    now = datetime.now(timezone.utc)
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO admin_audit_log (
                    admin_user_id, action_type, subject_key, wallet_id, operation_id, created_at, event_type, details, applied_at
                ) VALUES
                ('admin-a', 'WALLET_UNLOCK', 'w1', 'w1', NULL, :old, 'WALLET_UNLOCK', '{}', :old),
                ('admin-b', 'OPERATION_CORRECTION', 'op-1', 'w1', 'op-1', :mid, 'OPERATION_CORRECTION', '{}', :mid),
                ('admin-c', 'OPERATION_CORRECTION', 'op-2', 'w2', 'op-2', :new, 'OPERATION_CORRECTION', '{}', :new)
                """
            ),
            {"old": now - timedelta(days=3), "mid": now - timedelta(days=1), "new": now},
        )

    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("SIDECAR_INTERNAL_TOKENS", "test-token")
    get_settings.cache_clear()
    override_engine(engine)
    client = TestClient(app)

    page = client.get("/admin/audit-log?wallet_id=w1&limit=1&offset=0", headers=_headers())
    assert page.status_code == 200
    payload = page.json()
    assert payload["total"] == 2
    assert len(payload["items"]) == 1

    bounded = client.get(
        "/admin/audit-log",
        params={
            "from_timestamp": (now - timedelta(days=2)).isoformat(),
            "to_timestamp": now.isoformat(),
        },
        headers=_headers(),
    )
    assert bounded.status_code == 200
    assert [item["operation_id"] for item in bounded.json()["items"]] == ["op-2", "op-1"]


def test_phase4_spend_report_endpoint_aggregates_costs(tmp_path: Path, monkeypatch) -> None:
    engine = _build_engine(tmp_path)
    _seed(engine)
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("SIDECAR_INTERNAL_TOKENS", "test-token")
    get_settings.cache_clear()
    override_engine(engine)

    _reserve_and_settle(engine, "spend-1", "w1", Decimal("3.2"))
    _reserve_and_settle(engine, "spend-2", "w1", Decimal("2.8"))
    _reserve_and_settle(engine, "spend-3", "w2", Decimal("1.5"))

    client = TestClient(app)
    response = client.get("/admin/spend-report?wallet_id=w1", headers=_headers())
    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 1
    assert items[0]["wallet_id"] == "w1"
    assert items[0]["operations"] == 2
    assert items[0]["total_cost"] == "6.000000"


def test_phase4_wallet_summary_endpoint(tmp_path: Path, monkeypatch) -> None:
    engine = _build_engine(tmp_path)
    _seed(engine)
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("SIDECAR_INTERNAL_TOKENS", "test-token")
    get_settings.cache_clear()
    override_engine(engine)

    _reserve_and_settle(engine, "sum-1", "w1", Decimal("2.0"))
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                UPDATE user_wallets
                SET active = FALSE, lock_reason = 'MANUAL_REVIEW', locked_at = CURRENT_TIMESTAMP
                WHERE user_id = 'w1'
                """
            )
        )

    client = TestClient(app)
    response = client.get("/admin/wallet-summary/w1", headers=_headers())
    assert response.status_code == 200
    payload = response.json()
    assert payload["wallet_id"] == "w1"
    assert payload["locked"] is True
    assert payload["lock_reason"] == "MANUAL_REVIEW"
    assert payload["last_event_type"] is not None
