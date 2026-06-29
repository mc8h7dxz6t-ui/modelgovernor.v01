from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from uuid import uuid4
import os
import sys

import pytest

pytest.importorskip("psycopg")
import psycopg
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.orm import Session, sessionmaker

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from reconciler.app.sweeper import sweep_expired_reservations
from sidecar.app.config import Settings
from sidecar.app.ledger import ConflictError, TraceCapExceededError, apply_settlement, reserve_operation
from sidecar.app.schemas import ReserveRequest, SettleRequest
from tests.support.pg_migrations import iter_pg_sql_statements

MIGRATIONS_DIR = REPO_ROOT / "migrations"
MIGRATION_FILES = sorted(MIGRATIONS_DIR.glob("*.sql"))


def _postgres_test_url() -> str:
    database_url = os.getenv("POSTGRES_TEST_URL")
    if not database_url:
        pytest.skip("POSTGRES_TEST_URL not set; skipping Postgres-backed proof tests")
    return database_url


def _to_psycopg_dsn(database_url: str) -> str:
    if database_url.startswith("postgresql+psycopg://"):
        return database_url.replace("postgresql+psycopg://", "postgresql://", 1)
    return database_url


@contextmanager
def _isolated_database(base_url: str):
    base = make_url(base_url)
    resolved_password = (
        base.password
        or os.getenv("POSTGRES_TEST_PASSWORD")
        or os.getenv("POSTGRES_PASSWORD")
        or "postgres"
    )

    admin_url = _to_psycopg_dsn(
        URL.create(
            drivername="postgresql",
            username=base.username,
            password=resolved_password,
            host=base.host,
            port=base.port,
            database=base.database or "postgres",
        ).render_as_string(hide_password=False)
    )
    db_name = f"mgov_test_{uuid4().hex[:12]}"

    with psycopg.connect(admin_url, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute(f'CREATE DATABASE "{db_name}"')

    test_url = URL.create(
        drivername="postgresql+psycopg",
        username=base.username,
        password=resolved_password,
        host=base.host,
        port=base.port,
        database=db_name,
    ).render_as_string(hide_password=False)

    try:
        yield test_url
    finally:
        with psycopg.connect(admin_url, autocommit=True) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT pg_terminate_backend(pid)
                    FROM pg_stat_activity
                    WHERE datname = %s AND pid <> pg_backend_pid()
                    """,
                    (db_name,),
                )
                cur.execute(f'DROP DATABASE IF EXISTS "{db_name}"')


def _apply_migrations(database_url: str) -> None:
    dsn = _to_psycopg_dsn(database_url)
    with psycopg.connect(dsn, autocommit=True) as conn:
        with conn.cursor() as cur:
            for migration_file in MIGRATION_FILES:
                script = migration_file.read_text(encoding="utf-8")
                for statement in iter_pg_sql_statements(script):
                    cur.execute(f"{statement};")


def _settings(database_url: str, *, default_trace_cap_amount: Decimal = Decimal("25.000000")) -> Settings:
    return Settings(
        database_url=database_url,
        redis_url="redis://example/0",
        sidecar_internal_tokens="test-token",
        default_trace_cap_amount=default_trace_cap_amount,
        drift_absolute_tolerance=Decimal("0.500000"),
        drift_ratio_tolerance=Decimal("0.050000"),
        manual_approval_cost_threshold=Decimal("1000000"),
        default_run_budget_amount=Decimal("1000000"),
        default_session_budget_amount=Decimal("1000000"),
        default_user_budget_amount=Decimal("1000000"),
        default_tenant_budget_amount=Decimal("1000000"),
        db_pool_size=5,
        db_max_overflow=5,
        db_pool_timeout_seconds=5,
        db_pool_recycle_seconds=1800,
    )


def _seed_wallet(engine, user_id: str, balance: Decimal = Decimal("100.000000")) -> None:
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO user_wallets (user_id, balance, active)
                VALUES (:user_id, :balance, TRUE)
                ON CONFLICT (user_id) DO UPDATE SET balance = EXCLUDED.balance, active = TRUE
                """
            ),
            {"user_id": user_id, "balance": balance},
        )


def test_contested_trace_cap_reservations_on_same_trace_postgres() -> None:
    base_url = _postgres_test_url()
    with _isolated_database(base_url) as database_url:
        _apply_migrations(database_url)
        engine = create_engine(database_url, future=True)
        settings = _settings(database_url, default_trace_cap_amount=Decimal("10.000000"))
        _seed_wallet(engine, "user-1", Decimal("100.000000"))

        factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

        def reserve_once(op_key: str) -> str:
            with factory() as session:
                try:
                    reserve_operation(
                        session,
                        settings,
                        ReserveRequest(
                            user_id="user-1",
                            trace_id="trace-race",
                            idempotency_key=op_key,
                            model="gpt-4o-mini",
                            estimated_cost=Decimal("6.000000"),
                        ),
                    )
                    return "reserved"
                except TraceCapExceededError:
                    session.rollback()
                    return "trace_cap_exceeded"

        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = sorted(pool.map(reserve_once, ["race-a", "race-b"]))

        with Session(engine) as session:
            reserved_total = session.execute(
                text("SELECT reserved_total FROM trace_budget_state WHERE trace_id = 'trace-race'")
            ).scalar_one()
            ledger_rows = session.execute(
                text("SELECT COUNT(*) FROM escrow_ledger WHERE trace_id = 'trace-race'")
            ).scalar_one()

        assert outcomes == ["reserved", "trace_cap_exceeded"]
        assert Decimal(reserved_total) == Decimal("6.000000")
        assert ledger_rows == 1


def test_concurrent_reconciler_workers_do_not_double_process_expired_rows_postgres() -> None:
    base_url = _postgres_test_url()
    with _isolated_database(base_url) as database_url:
        _apply_migrations(database_url)
        engine = create_engine(database_url, future=True)
        settings = _settings(database_url)
        _seed_wallet(engine, "user-1", Decimal("100.000000"))

        for key in ["exp-a", "exp-b"]:
            with Session(engine) as session:
                reserve_operation(
                    session,
                    settings,
                    ReserveRequest(
                        user_id="user-1",
                        trace_id=f"trace-{key}",
                        idempotency_key=key,
                        model="gpt-4o-mini",
                        estimated_cost=Decimal("10.000000"),
                    ),
                )

        with engine.begin() as connection:
            connection.execute(
                text(
                    """
                    UPDATE escrow_ledger
                    SET expires_at = :expires_at
                    WHERE idempotency_key IN ('exp-a', 'exp-b')
                    """
                ),
                {"expires_at": datetime.now(timezone.utc) - timedelta(minutes=2)},
            )

        def sweep_worker() -> int:
            with Session(engine) as session:
                return sweep_expired_reservations(session, batch_size=2)

        with ThreadPoolExecutor(max_workers=2) as pool:
            swept_counts = list(pool.map(lambda _: sweep_worker(), [1, 2]))

        with Session(engine) as session:
            statuses = session.execute(
                text(
                    """
                    SELECT idempotency_key, status
                    FROM escrow_ledger
                    WHERE idempotency_key IN ('exp-a', 'exp-b')
                    ORDER BY idempotency_key
                    """
                )
            ).mappings().all()
            wallet_balance = session.execute(
                text("SELECT balance FROM user_wallets WHERE user_id = 'user-1'")
            ).scalar_one()

        assert sum(swept_counts) == 2
        assert statuses == [
            {"idempotency_key": "exp-a", "status": "EXPIRED"},
            {"idempotency_key": "exp-b", "status": "EXPIRED"},
        ]
        assert Decimal(wallet_balance) == Decimal("100.000000")


def test_provider_request_id_uniqueness_conflict_handling_postgres() -> None:
    base_url = _postgres_test_url()
    with _isolated_database(base_url) as database_url:
        _apply_migrations(database_url)
        engine = create_engine(database_url, future=True)
        settings = _settings(database_url)
        _seed_wallet(engine, "user-1", Decimal("100.000000"))

        for key in ["op-uniq-1", "op-uniq-2"]:
            with Session(engine) as session:
                reserve_operation(
                    session,
                    settings,
                    ReserveRequest(
                        user_id="user-1",
                        trace_id=f"trace-{key}",
                        idempotency_key=key,
                        model="gpt-4o-mini",
                        estimated_cost=Decimal("5.000000"),
                    ),
                )

        with Session(engine) as session:
            apply_settlement(
                session,
                settings,
                SettleRequest(
                    idempotency_key="op-uniq-1",
                    outcome="IN_FLIGHT",
                    dispatch_attempt_key="attempt-uniq-1",
                    provider_name="openai",
                    model="gpt-4o-mini",
                    provider_request_id="provider-duplicate",
                ),
            )

        with Session(engine) as session:
            with pytest.raises(ConflictError, match="provider_request_id"):
                apply_settlement(
                    session,
                    settings,
                    SettleRequest(
                        idempotency_key="op-uniq-2",
                        outcome="IN_FLIGHT",
                        dispatch_attempt_key="attempt-uniq-2",
                        provider_name="openai",
                        model="gpt-4o-mini",
                        provider_request_id="provider-duplicate",
                    ),
                )


def test_late_settlement_after_stranded_hold_postgres() -> None:
    base_url = _postgres_test_url()
    with _isolated_database(base_url) as database_url:
        _apply_migrations(database_url)
        engine = create_engine(database_url, future=True)
        settings = _settings(database_url)
        _seed_wallet(engine, "user-1", Decimal("100.000000"))

        with Session(engine) as session:
            reserve_operation(
                session,
                settings,
                ReserveRequest(
                    user_id="user-1",
                    trace_id="trace-late",
                    idempotency_key="late-op",
                    model="gpt-4o-mini",
                    estimated_cost=Decimal("10.000000"),
                ),
            )

        with Session(engine) as session:
            apply_settlement(
                session,
                settings,
                SettleRequest(
                    idempotency_key="late-op",
                    outcome="IN_FLIGHT",
                    dispatch_attempt_key="late-attempt",
                    provider_name="openai",
                    model="gpt-4o-mini",
                    provider_request_id="provider-late",
                ),
            )

        with Session(engine) as session:
            apply_settlement(
                session,
                settings,
                SettleRequest(
                    idempotency_key="late-op",
                    outcome="PROVIDER_TIMEOUT",
                    dispatch_attempt_key="late-attempt",
                    provider_name="openai",
                    model="gpt-4o-mini",
                    provider_request_id="provider-late",
                    reason="upstream_timeout",
                ),
            )

        with engine.begin() as connection:
            connection.execute(
                text(
                    "UPDATE escrow_ledger SET expires_at = :expires_at WHERE idempotency_key = 'late-op'"
                ),
                {"expires_at": datetime.now(timezone.utc) - timedelta(minutes=2)},
            )

        with Session(engine) as session:
            assert sweep_expired_reservations(session, batch_size=10) == 1

        with Session(engine) as session:
            stranded_row = session.execute(
                text("SELECT status, terminal_reason FROM escrow_ledger WHERE idempotency_key = 'late-op'")
            ).mappings().one()
            balance_after_sweep = session.execute(
                text("SELECT balance FROM user_wallets WHERE user_id = 'user-1'")
            ).scalar_one()

        assert stranded_row["status"] == "STRANDED"
        assert stranded_row["terminal_reason"] == "STRANDED_HOLD_PENDING_RECONCILIATION"
        assert Decimal(balance_after_sweep) == Decimal("90.000000")

        with Session(engine) as session:
            apply_settlement(
                session,
                settings,
                SettleRequest(
                    provider_request_id="provider-late",
                    outcome="SETTLED",
                    actual_cost=Decimal("12.000000"),
                    dispatch_attempt_key="late-attempt",
                    provider_name="openai",
                    model="gpt-4o-mini",
                ),
            )

        with Session(engine) as session:
            final_ledger = session.execute(
                text(
                    "SELECT status, terminal_reason, actual_amount FROM escrow_ledger WHERE idempotency_key = 'late-op'"
                )
            ).mappings().one()
            wallet = session.execute(
                text("SELECT balance, active, lock_reason FROM user_wallets WHERE user_id = 'user-1'")
            ).mappings().one()

        assert final_ledger["status"] == "SETTLED"
        assert final_ledger["terminal_reason"] == "RECONCILED_LATE_SETTLE"
        assert Decimal(final_ledger["actual_amount"]) == Decimal("12.000000")
        assert Decimal(wallet["balance"]) == Decimal("88.000000")
        assert wallet["active"] is False
        assert wallet["lock_reason"] == "DRIFT_THRESHOLD_EXCEEDED"
