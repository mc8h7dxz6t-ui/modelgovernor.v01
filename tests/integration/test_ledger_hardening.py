from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
import sqlite3
import sys

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

sqlite3.register_adapter(Decimal, lambda value: str(value))

from reconciler.app.sweeper import sweep_expired_reservations
from sidecar.app.config import Settings
from sidecar.app.ledger import ConflictError, TraceCapExceededError, apply_settlement, reserve_operation
from sidecar.app.schemas import ReserveRequest, SettleRequest


def test_reserve_dispatch_settle_happy_path_and_replay(tmp_path: Path) -> None:
    engine = _create_test_engine(tmp_path / "happy.sqlite3")
    settings = _settings(engine)
    _bootstrap_schema(engine)
    _seed_wallet_and_model(engine, user_id="user-1")

    with Session(engine) as session:
        reserve_result = reserve_operation(
            session,
            settings,
            ReserveRequest(
                user_id="user-1",
                trace_id="trace-1",
                idempotency_key="op-1",
                model="gpt-4o-mini",
                estimated_cost=Decimal("10"),
            ),
        )
        assert reserve_result.status == "RESERVED"
        assert reserve_result.actual_amount == Decimal("10.000000")

    with Session(engine) as session:
        replay_result = reserve_operation(
            session,
            settings,
            ReserveRequest(
                user_id="user-1",
                trace_id="trace-1",
                idempotency_key="op-1",
                model="gpt-4o-mini",
                estimated_cost=Decimal("10"),
            ),
        )
        assert replay_result.status == "RESERVED"
        assert replay_result.actual_amount == Decimal("10.000000")

    with Session(engine) as session:
        in_flight = apply_settlement(
            session,
            settings,
            SettleRequest(
                idempotency_key="op-1",
                outcome="IN_FLIGHT",
                dispatch_attempt_key="attempt-1",
                provider_name="openai",
                model="gpt-4o-mini",
                provider_request_id="provider-1",
            ),
        )
        assert in_flight.status == "IN_FLIGHT"

    with Session(engine) as session:
        settled = apply_settlement(
            session,
            settings,
            SettleRequest(
                idempotency_key="op-1",
                outcome="SETTLED",
                actual_cost=Decimal("7"),
                dispatch_attempt_key="attempt-1",
                provider_name="openai",
                model="gpt-4o-mini",
                provider_request_id="provider-1",
            ),
        )
        assert settled.status == "SETTLED"
        assert settled.actual_amount == Decimal("7.000000")

    with Session(engine) as session:
        wallet = session.execute(text("SELECT balance FROM user_wallets WHERE user_id = 'user-1'")).scalar_one()
        ledger = session.execute(
            text("SELECT status, terminal_reason FROM escrow_ledger WHERE idempotency_key = 'op-1'")
        ).mappings().one()
        events = session.execute(
            text("SELECT event_type FROM ledger_events WHERE idempotency_key = 'op-1' ORDER BY event_id")
        ).scalars().all()

    assert Decimal(wallet) == Decimal("93.000000")
    assert ledger["status"] == "SETTLED"
    assert ledger["terminal_reason"] == "SETTLED_FINAL"
    assert events == [
        "RESERVE_CREATED",
        "DISPATCH_STARTED",
        "SETTLEMENT_REFUND",
        "SETTLED_FINAL",
    ]


def test_duplicate_reserve_conflict_but_failover_attempts_are_allowed(tmp_path: Path) -> None:
    engine = _create_test_engine(tmp_path / "failover.sqlite3")
    settings = _settings(engine)
    _bootstrap_schema(engine)
    _seed_wallet_and_model(engine, user_id="user-1")

    with Session(engine) as session:
        reserve_operation(
            session,
            settings,
            ReserveRequest(
                user_id="user-1",
                trace_id="trace-2",
                idempotency_key="op-2",
                model="gpt-4o-mini",
                estimated_cost=Decimal("8"),
            ),
        )

    with Session(engine) as session:
        try:
            reserve_operation(
                session,
                settings,
                ReserveRequest(
                    user_id="user-1",
                    trace_id="trace-2",
                    idempotency_key="op-2",
                    model="claude-3-5-sonnet",
                    estimated_cost=Decimal("8"),
                ),
            )
        except ConflictError:
            pass
        else:
            raise AssertionError("expected duplicate reserve conflict")

    with Session(engine) as session:
        apply_settlement(
            session,
            settings,
            SettleRequest(
                idempotency_key="op-2",
                outcome="IN_FLIGHT",
                dispatch_attempt_key="attempt-a",
                provider_name="openai",
                model="gpt-4o-mini",
                provider_request_id="provider-a",
            ),
        )

    with Session(engine) as session:
        apply_settlement(
            session,
            settings,
            SettleRequest(
                idempotency_key="op-2",
                outcome="PROVIDER_TIMEOUT",
                dispatch_attempt_key="attempt-a",
                provider_name="openai",
                model="gpt-4o-mini",
                provider_request_id="provider-a",
                reason="gateway_timeout",
            ),
        )

    with Session(engine) as session:
        apply_settlement(
            session,
            settings,
            SettleRequest(
                idempotency_key="op-2",
                outcome="IN_FLIGHT",
                dispatch_attempt_key="attempt-b",
                provider_name="anthropic",
                model="claude-3-5-sonnet",
                provider_request_id="provider-b",
            ),
        )

    with Session(engine) as session:
        settled = apply_settlement(
            session,
            settings,
            SettleRequest(
                idempotency_key="op-2",
                outcome="SETTLED",
                actual_cost=Decimal("8"),
                dispatch_attempt_key="attempt-b",
                provider_name="anthropic",
                model="claude-3-5-sonnet",
                provider_request_id="provider-b",
            ),
        )
        attempts = session.execute(
            text(
                """
                SELECT attempt_key, provider_name, status
                FROM provider_dispatch_attempts
                WHERE idempotency_key = 'op-2'
                ORDER BY attempt_key
                """
            )
        ).mappings().all()

    assert settled.status == "SETTLED"
    assert attempts == [
        {"attempt_key": "attempt-a", "provider_name": "openai", "status": "PROVIDER_TIMEOUT"},
        {"attempt_key": "attempt-b", "provider_name": "anthropic", "status": "SETTLED"},
    ]


def test_reconciler_strands_ambiguous_holds_and_accepts_late_authoritative_settle(tmp_path: Path) -> None:
    engine = _create_test_engine(tmp_path / "stranded.sqlite3")
    settings = _settings(engine)
    _bootstrap_schema(engine)
    _seed_wallet_and_model(engine, user_id="user-1")

    with Session(engine) as session:
        reserve_operation(
            session,
            settings,
            ReserveRequest(
                user_id="user-1",
                trace_id="trace-3",
                idempotency_key="op-3",
                model="gpt-4o-mini",
                estimated_cost=Decimal("10"),
            ),
        )

    with Session(engine) as session:
        apply_settlement(
            session,
            settings,
            SettleRequest(
                idempotency_key="op-3",
                outcome="IN_FLIGHT",
                dispatch_attempt_key="attempt-3",
                provider_name="openai",
                model="gpt-4o-mini",
                provider_request_id="provider-3",
            ),
        )

    with Session(engine) as session:
        apply_settlement(
            session,
            settings,
            SettleRequest(
                idempotency_key="op-3",
                outcome="PROVIDER_TIMEOUT",
                dispatch_attempt_key="attempt-3",
                provider_name="openai",
                model="gpt-4o-mini",
                provider_request_id="provider-3",
                reason="upstream_timeout",
            ),
        )
        session.execute(
            text("UPDATE escrow_ledger SET expires_at = :expires_at WHERE idempotency_key = 'op-3'"),
            {"expires_at": datetime.now(timezone.utc) - timedelta(minutes=1)},
        )
        session.commit()

    with Session(engine) as session:
        assert sweep_expired_reservations(session, batch_size=10) == 1

    with Session(engine) as session:
        stranded = session.execute(
            text(
                "SELECT status, terminal_reason FROM escrow_ledger WHERE idempotency_key = 'op-3'"
            )
        ).mappings().one()
        balance = session.execute(text("SELECT balance FROM user_wallets WHERE user_id = 'user-1'")).scalar_one()

    assert stranded["status"] == "STRANDED"
    assert stranded["terminal_reason"] == "STRANDED_HOLD_PENDING_RECONCILIATION"
    assert Decimal(balance) == Decimal("90.000000")

    with Session(engine) as session:
        apply_settlement(
            session,
            settings,
            SettleRequest(
                provider_request_id="provider-3",
                outcome="SETTLED",
                actual_cost=Decimal("12"),
                dispatch_attempt_key="attempt-3",
                provider_name="openai",
                model="gpt-4o-mini",
            ),
        )

    with Session(engine) as session:
        ledger = session.execute(
            text(
                """
                SELECT status, terminal_reason, actual_amount
                FROM escrow_ledger
                WHERE idempotency_key = 'op-3'
                """
            )
        ).mappings().one()
        wallet = session.execute(
            text("SELECT balance, active, lock_reason FROM user_wallets WHERE user_id = 'user-1'")
        ).mappings().one()
        events = session.execute(
            text(
                """
                SELECT event_type
                FROM ledger_events
                WHERE idempotency_key = 'op-3'
                ORDER BY event_id
                """
            )
        ).scalars().all()

    assert ledger["status"] == "SETTLED"
    assert ledger["terminal_reason"] == "RECONCILED_LATE_SETTLE"
    assert Decimal(ledger["actual_amount"]) == Decimal("12.000000")
    assert Decimal(wallet["balance"]) == Decimal("88.000000")
    assert wallet["active"] == 0
    assert wallet["lock_reason"] == "DRIFT_THRESHOLD_EXCEEDED"
    assert "STRANDED_HOLD" in events
    assert "DRIFT_ENFORCED" in events


def test_reconciler_refunds_undispatched_expiry_and_late_settle_appends_correction(tmp_path: Path) -> None:
    engine = _create_test_engine(tmp_path / "expired.sqlite3")
    settings = _settings(engine)
    _bootstrap_schema(engine)
    _seed_wallet_and_model(engine, user_id="user-1")

    with Session(engine) as session:
        reserve_operation(
            session,
            settings,
            ReserveRequest(
                user_id="user-1",
                trace_id="trace-4",
                idempotency_key="op-4",
                model="gpt-4o-mini",
                estimated_cost=Decimal("10"),
            ),
        )
        session.execute(
            text("UPDATE escrow_ledger SET expires_at = :expires_at WHERE idempotency_key = 'op-4'"),
            {"expires_at": datetime.now(timezone.utc) - timedelta(minutes=1)},
        )
        session.commit()

    with Session(engine) as session:
        assert sweep_expired_reservations(session, batch_size=10) == 1

    with Session(engine) as session:
        expired = session.execute(
            text("SELECT status FROM escrow_ledger WHERE idempotency_key = 'op-4'")
        ).scalar_one()
        balance = session.execute(text("SELECT balance FROM user_wallets WHERE user_id = 'user-1'")).scalar_one()

    assert expired == "EXPIRED"
    assert Decimal(balance) == Decimal("100.000000")

    with Session(engine) as session:
        apply_settlement(
            session,
            settings,
            SettleRequest(
                idempotency_key="op-4",
                outcome="SETTLED",
                actual_cost=Decimal("4"),
                provider_request_id="provider-4",
            ),
        )

    with Session(engine) as session:
        wallet = session.execute(text("SELECT balance FROM user_wallets WHERE user_id = 'user-1'")).scalar_one()
        events = session.execute(
            text(
                """
                SELECT event_type
                FROM ledger_events
                WHERE idempotency_key = 'op-4'
                ORDER BY event_id
                """
            )
        ).scalars().all()

    assert Decimal(wallet) == Decimal("96.000000")
    assert "EXPIRED_SWEEP" in events
    assert "SETTLEMENT_CORRECTION_DEBIT" in events
    assert "RECONCILED_LATE_SETTLE" in events


def test_drift_tolerance_separates_low_noise_from_enforcement(tmp_path: Path) -> None:
    engine = _create_test_engine(tmp_path / "drift.sqlite3")
    settings = _settings(
        engine,
        drift_absolute_tolerance=Decimal("0.500000"),
        drift_ratio_tolerance=Decimal("0.050000"),
    )
    _bootstrap_schema(engine)
    _seed_wallet_and_model(engine, user_id="user-low")
    _seed_wallet_and_model(engine, user_id="user-high")

    for user_id, key, actual_cost in [
        ("user-low", "op-low", Decimal("10.400000")),
        ("user-high", "op-high", Decimal("11.000000")),
    ]:
        with Session(engine) as session:
            reserve_operation(
                session,
                settings,
                ReserveRequest(
                    user_id=user_id,
                    trace_id=f"trace-{user_id}",
                    idempotency_key=key,
                    model="gpt-4o-mini",
                    estimated_cost=Decimal("10"),
                ),
            )
        with Session(engine) as session:
            apply_settlement(
                session,
                settings,
                SettleRequest(
                    idempotency_key=key,
                    outcome="SETTLED",
                    actual_cost=actual_cost,
                    provider_request_id=f"provider-{key}",
                ),
            )

    with Session(engine) as session:
        low_user = session.execute(
            text("SELECT active FROM user_wallets WHERE user_id = 'user-low'")
        ).scalar_one()
        high_user = session.execute(
            text("SELECT active FROM user_wallets WHERE user_id = 'user-high'")
        ).scalar_one()
        low_events = session.execute(
            text("SELECT event_type FROM ledger_events WHERE idempotency_key = 'op-low' ORDER BY event_id")
        ).scalars().all()
        high_events = session.execute(
            text("SELECT event_type FROM ledger_events WHERE idempotency_key = 'op-high' ORDER BY event_id")
        ).scalars().all()

    assert low_user == 1
    assert high_user == 0
    assert "DRIFT_TOLERATED" in low_events
    assert "DRIFT_ENFORCED" in high_events


def test_concurrent_reserves_cannot_oversubscribe_trace_cap(tmp_path: Path) -> None:
    engine = _create_test_engine(tmp_path / "concurrency.sqlite3")
    settings = _settings(engine, default_trace_cap_amount=Decimal("10.000000"))
    _bootstrap_schema(engine)
    _seed_wallet_and_model(engine, user_id="user-1", balance=Decimal("100"))
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

    def attempt_reserve(operation_key: str) -> str:
        with factory() as session:
            try:
                reserve_operation(
                    session,
                    settings,
                    ReserveRequest(
                        user_id="user-1",
                        trace_id="trace-concurrent",
                        idempotency_key=operation_key,
                        model="gpt-4o-mini",
                        estimated_cost=Decimal("6"),
                    ),
                )
                return "reserved"
            except TraceCapExceededError:
                session.rollback()
                return "trace_cap_exceeded"

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = sorted(pool.map(attempt_reserve, ["op-a", "op-b"]))

    with Session(engine) as session:
        trace_state = session.execute(
            text(
                """
                SELECT reserved_total
                FROM trace_budget_state
                WHERE trace_id = 'trace-concurrent'
                """
            )
        ).scalar_one()
        ledger_count = session.execute(text("SELECT COUNT(*) FROM escrow_ledger")).scalar_one()

    assert results == ["reserved", "trace_cap_exceeded"]
    assert Decimal(trace_state) == Decimal("6.000000")
    assert ledger_count == 1


def _settings(
    engine,
    *,
    reserve_ttl_seconds: int = 300,
    default_trace_cap_amount: Decimal = Decimal("25.000000"),
    drift_absolute_tolerance: Decimal = Decimal("0.500000"),
    drift_ratio_tolerance: Decimal = Decimal("0.050000"),
) -> Settings:
    return Settings(
        database_url=str(engine.url),
        redis_url="redis://example/0",
        sidecar_internal_tokens="test-token",
        reserve_ttl_seconds=reserve_ttl_seconds,
        default_trace_cap_amount=default_trace_cap_amount,
        drift_absolute_tolerance=drift_absolute_tolerance,
        drift_ratio_tolerance=drift_ratio_tolerance,
        db_pool_size=2,
        db_max_overflow=1,
        db_pool_timeout_seconds=5,
        db_pool_recycle_seconds=1800,
    )


def _create_test_engine(path: Path):
    engine = create_engine(
        f"sqlite:///{path}",
        future=True,
        connect_args={"check_same_thread": False},
    )
    with engine.begin() as connection:
        connection.execute(text("PRAGMA journal_mode=WAL"))
    return engine


def _bootstrap_schema(engine) -> None:
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE user_wallets (
                    user_id TEXT PRIMARY KEY,
                    balance NUMERIC(18, 6) NOT NULL DEFAULT 100.000000,
                    active BOOLEAN NOT NULL DEFAULT TRUE,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    locked_at TIMESTAMP,
                    lock_reason TEXT
                )
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE TABLE model_policy_registry (
                    model_name TEXT PRIMARY KEY,
                    provider TEXT NOT NULL,
                    enabled BOOLEAN NOT NULL DEFAULT TRUE,
                    max_input_tokens INTEGER NOT NULL,
                    max_output_tokens INTEGER NOT NULL,
                    max_cost_per_request NUMERIC(18, 6) NOT NULL,
                    stream_allowed BOOLEAN NOT NULL DEFAULT TRUE,
                    fallback_price_per_token NUMERIC(18, 6) NOT NULL,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE TABLE escrow_ledger (
                    idempotency_key TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    trace_id TEXT NOT NULL,
                    model TEXT NOT NULL,
                    request_fingerprint TEXT NOT NULL,
                    reserved_amount NUMERIC(18, 6) NOT NULL,
                    actual_amount NUMERIC(18, 6) NOT NULL DEFAULT 0.000000,
                    status TEXT NOT NULL,
                    provider_request_id TEXT,
                    terminal_reason TEXT,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP NOT NULL,
                    settled_at TIMESTAMP,
                    expired_at TIMESTAMP,
                    reconciled BOOLEAN NOT NULL DEFAULT FALSE,
                    trace_cap_amount NUMERIC(18, 6) NOT NULL DEFAULT 25.000000,
                    dispatch_started_at TIMESTAMP,
                    drift_amount NUMERIC(18, 6) NOT NULL DEFAULT 0.000000
                )
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE TABLE ledger_events (
                    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    idempotency_key TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    amount_delta NUMERIC(18, 6) NOT NULL,
                    metadata TEXT NOT NULL DEFAULT '{}',
                    recorded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE TABLE trace_budget_state (
                    trace_id TEXT PRIMARY KEY,
                    cap_amount NUMERIC(18, 6) NOT NULL,
                    reserved_total NUMERIC(18, 6) NOT NULL DEFAULT 0.000000,
                    settled_total NUMERIC(18, 6) NOT NULL DEFAULT 0.000000,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE TABLE provider_dispatch_attempts (
                    attempt_key TEXT PRIMARY KEY,
                    idempotency_key TEXT NOT NULL,
                    provider_name TEXT,
                    model_name TEXT,
                    provider_request_id TEXT,
                    status TEXT NOT NULL,
                    terminal_reason TEXT,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        )
        connection.execute(
            text("CREATE UNIQUE INDEX idx_attempt_provider_request ON provider_dispatch_attempts (provider_request_id)")
        )


def _seed_wallet_and_model(engine, *, user_id: str, balance: Decimal = Decimal("100")) -> None:
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO user_wallets (user_id, balance, active)
                VALUES (:user_id, :balance, TRUE)
                """
            ),
            {"user_id": user_id, "balance": balance},
        )
        connection.execute(
            text(
                """
                INSERT OR IGNORE INTO model_policy_registry (
                    model_name,
                    provider,
                    enabled,
                    max_input_tokens,
                    max_output_tokens,
                    max_cost_per_request,
                    stream_allowed,
                    fallback_price_per_token
                ) VALUES (
                    'gpt-4o-mini',
                    'openai',
                    TRUE,
                    8192,
                    8192,
                    100.000000,
                    TRUE,
                    0.000010
                )
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT OR IGNORE INTO model_policy_registry (
                    model_name,
                    provider,
                    enabled,
                    max_input_tokens,
                    max_output_tokens,
                    max_cost_per_request,
                    stream_allowed,
                    fallback_price_per_token
                ) VALUES (
                    'claude-3-5-sonnet',
                    'anthropic',
                    TRUE,
                    8192,
                    8192,
                    100.000000,
                    TRUE,
                    0.000020
                )
                """
            )
        )
