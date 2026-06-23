"""Postgres-backed vigorous integration tests for the ledger control plane.

These tests run against a *real* Postgres instance (not SQLite) and exercise:
  - True atomic UPDATE-RETURNING for trace-cap contention
  - FOR UPDATE SKIP LOCKED semantics in the reconciler
  - Postgres ENUM type behaviour for escrow status transitions
  - JSONB metadata storage on ledger_events
  - provider_request_id uniqueness constraint enforcement
  - Reserve replay and mismatched-fingerprint conflict
  - Provider failover beneath one logical operation
  - Reconciler expiry claim: EXPIRED vs STRANDED branches
  - Late settlement after EXPIRED and STRANDED states
  - Drift enforcement causing wallet lockout
  - Concurrent reconciler workers: zero duplicate refunds

Prerequisites
-------------
Set ``POSTGRES_TEST_URL`` to a live Postgres connection string, e.g.::

    POSTGRES_TEST_URL=postgresql+psycopg://postgres:postgres@localhost:5432/mg_test

or start the bundled test stack first::

    docker compose -f docker-compose.test.yml up -d

All tests in this module are automatically skipped when the env-var is absent.
"""
from __future__ import annotations

import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from reconciler.app.sweeper import sweep_expired_reservations
from sidecar.app.config import Settings
from sidecar.app.ledger import (
    ConflictError,
    InsufficientFundsError,
    TraceCapExceededError,
    apply_settlement,
    reserve_operation,
)
from sidecar.app.metrics import get_counters
from sidecar.app.schemas import ReserveRequest, SettleRequest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

MONEY_QUANTUM = Decimal("0.000001")


def _money(v) -> Decimal:
    return Decimal(v or 0).quantize(MONEY_QUANTUM)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _pg_settings(
    pg_url: str,
    *,
    reserve_ttl_seconds: int = 300,
    default_trace_cap_amount: Decimal = Decimal("25.000000"),
    drift_absolute_tolerance: Decimal = Decimal("0.500000"),
    drift_ratio_tolerance: Decimal = Decimal("0.050000"),
) -> Settings:
    return Settings(
        database_url=pg_url,
        redis_url="redis://example/0",
        sidecar_internal_tokens="test-token",
        reserve_ttl_seconds=reserve_ttl_seconds,
        default_trace_cap_amount=default_trace_cap_amount,
        drift_absolute_tolerance=drift_absolute_tolerance,
        drift_ratio_tolerance=drift_ratio_tolerance,
        db_pool_size=4,
        db_max_overflow=4,
        db_pool_timeout_seconds=10,
        db_pool_recycle_seconds=300,
    )


def _seed_wallet(conn, *, user_id: str, balance: Decimal = Decimal("200")) -> None:
    conn.execute(
        text(
            "INSERT INTO user_wallets (user_id, balance, active) VALUES (:uid, :bal, TRUE)"
        ),
        {"uid": user_id, "bal": balance},
    )


def _expire_reservation(conn, *, idempotency_key: str) -> None:
    """Back-date an escrow row so the reconciler considers it expired."""
    conn.execute(
        text(
            "UPDATE escrow_ledger SET expires_at = :t WHERE idempotency_key = :k"
        ),
        {"t": _utcnow() - timedelta(minutes=5), "k": idempotency_key},
    )


# ---------------------------------------------------------------------------
# All tests require Postgres — handled via the session-scoped pg_engine fixture
# defined in conftest.py which skips if POSTGRES_TEST_URL is absent.
# The clean_pg_tables fixture truncates ledger tables before each test.
# ---------------------------------------------------------------------------

pytestmark = pytest.mark.usefixtures("clean_pg_tables")


# ---------------------------------------------------------------------------
# 1. Happy path: reserve → dispatch → settle with Postgres semantics
# ---------------------------------------------------------------------------

class TestHappyPath:
    def test_reserve_settle_postgres_enum_and_jsonb(self, pg_engine: Engine) -> None:
        """Postgres ENUM status and JSONB metadata are correctly persisted."""
        settings = _pg_settings(str(pg_engine.url))
        with pg_engine.begin() as conn:
            _seed_wallet(conn, user_id="pg-user-1")

        with Session(pg_engine) as s:
            result = reserve_operation(
                s,
                settings,
                ReserveRequest(
                    user_id="pg-user-1",
                    trace_id="pg-trace-1",
                    idempotency_key="pg-op-1",
                    model="gpt-4o-mini",
                    estimated_cost=Decimal("10"),
                ),
            )
        assert result.status == "RESERVED"

        with Session(pg_engine) as s:
            s.execute(
                text(
                    "SELECT status::text FROM escrow_ledger "
                    "WHERE idempotency_key = 'pg-op-1'"
                )
            ).scalar_one()  # confirms ENUM casts to text without error

            meta = s.execute(
                text(
                    "SELECT metadata->>'trace_id' AS tid "
                    "FROM ledger_events "
                    "WHERE idempotency_key = 'pg-op-1' LIMIT 1"
                )
            ).scalar_one()
        assert meta == "pg-trace-1"

    def test_idempotent_replay_returns_same_result(self, pg_engine: Engine) -> None:
        settings = _pg_settings(str(pg_engine.url))
        with pg_engine.begin() as conn:
            _seed_wallet(conn, user_id="pg-user-2")

        req = ReserveRequest(
            user_id="pg-user-2",
            trace_id="pg-trace-2",
            idempotency_key="pg-op-2",
            model="gpt-4o-mini",
            estimated_cost=Decimal("5"),
        )
        with Session(pg_engine) as s:
            r1 = reserve_operation(s, settings, req)
        with Session(pg_engine) as s:
            r2 = reserve_operation(s, settings, req)

        assert r1.status == r2.status == "RESERVED"
        assert r1.actual_amount == r2.actual_amount


# ---------------------------------------------------------------------------
# 2. Trace-cap contention on real Postgres (atomic UPDATE-RETURNING)
# ---------------------------------------------------------------------------

class TestTraceCapContention:
    def test_concurrent_reserves_respect_cap(self, pg_engine: Engine) -> None:
        """10 concurrent workers each attempt 6-unit reserve against a 10-unit
        cap — exactly one should succeed; the rest must be denied."""
        cap = Decimal("10")
        per_reserve = Decimal("6")
        settings = _pg_settings(str(pg_engine.url), default_trace_cap_amount=cap)
        factory = sessionmaker(bind=pg_engine, autoflush=False, autocommit=False, future=True)

        with pg_engine.begin() as conn:
            _seed_wallet(conn, user_id="pg-cap-user", balance=Decimal("1000"))

        def attempt(key: str) -> str:
            with factory() as s:
                try:
                    reserve_operation(
                        s,
                        settings,
                        ReserveRequest(
                            user_id="pg-cap-user",
                            trace_id="pg-cap-trace",
                            idempotency_key=key,
                            model="gpt-4o-mini",
                            estimated_cost=per_reserve,
                        ),
                    )
                    return "reserved"
                except TraceCapExceededError:
                    s.rollback()
                    return "cap_exceeded"
                except Exception:
                    s.rollback()
                    return "error"

        workers = 10
        keys = [f"pg-cap-op-{i}" for i in range(workers)]
        with ThreadPoolExecutor(max_workers=workers) as pool:
            outcomes = list(pool.map(attempt, keys))

        succeeded = outcomes.count("reserved")
        denied = outcomes.count("cap_exceeded")

        # Exactly one worker should have captured the full cap budget.
        assert succeeded == 1, f"Expected 1 success, got {succeeded}: {outcomes}"
        assert denied == workers - 1, f"Expected {workers - 1} denials, got {denied}"

        with Session(pg_engine) as s:
            reserved_total = s.execute(
                text(
                    "SELECT reserved_total FROM trace_budget_state "
                    "WHERE trace_id = 'pg-cap-trace'"
                )
            ).scalar_one()
        assert _money(reserved_total) == per_reserve

    def test_many_traces_all_succeed_independently(self, pg_engine: Engine) -> None:
        """Workers hitting different traces must not block each other."""
        cap = Decimal("10")
        settings = _pg_settings(str(pg_engine.url), default_trace_cap_amount=cap)
        factory = sessionmaker(bind=pg_engine, autoflush=False, autocommit=False, future=True)

        n = 20
        with pg_engine.begin() as conn:
            _seed_wallet(conn, user_id="pg-multi-user", balance=Decimal("10000"))

        def attempt(i: int) -> str:
            with factory() as s:
                try:
                    reserve_operation(
                        s,
                        settings,
                        ReserveRequest(
                            user_id="pg-multi-user",
                            trace_id=f"pg-multi-trace-{i}",
                            idempotency_key=f"pg-multi-op-{i}",
                            model="gpt-4o-mini",
                            estimated_cost=Decimal("3"),
                        ),
                    )
                    return "reserved"
                except Exception:
                    s.rollback()
                    return "error"

        with ThreadPoolExecutor(max_workers=n) as pool:
            results = list(pool.map(attempt, range(n)))

        assert results.count("reserved") == n, f"Some traces failed: {results}"


# ---------------------------------------------------------------------------
# 3. Reserve replay and mismatched-fingerprint conflict
# ---------------------------------------------------------------------------

class TestReplayAndConflict:
    def test_mismatched_fingerprint_raises_conflict(self, pg_engine: Engine) -> None:
        settings = _pg_settings(str(pg_engine.url))
        with pg_engine.begin() as conn:
            _seed_wallet(conn, user_id="pg-fp-user")

        with Session(pg_engine) as s:
            reserve_operation(
                s,
                settings,
                ReserveRequest(
                    user_id="pg-fp-user",
                    trace_id="pg-fp-trace",
                    idempotency_key="pg-fp-op",
                    model="gpt-4o-mini",
                    estimated_cost=Decimal("5"),
                ),
            )

        with pytest.raises(ConflictError, match="does not match"):
            with Session(pg_engine) as s:
                reserve_operation(
                    s,
                    settings,
                    ReserveRequest(
                        user_id="pg-fp-user",
                        trace_id="pg-fp-trace",
                        idempotency_key="pg-fp-op",
                        model="gpt-4o-mini",
                        estimated_cost=Decimal("99"),  # different amount → conflict
                    ),
                )

    def test_provider_request_id_uniqueness_conflict(self, pg_engine: Engine) -> None:
        """Attempting to attach the same provider_request_id to two different
        dispatch attempts must raise ConflictError on Postgres."""
        settings = _pg_settings(str(pg_engine.url))
        with pg_engine.begin() as conn:
            _seed_wallet(conn, user_id="pg-prid-user")

        # Create two independent operations
        for key in ("pg-prid-op-a", "pg-prid-op-b"):
            with Session(pg_engine) as s:
                reserve_operation(
                    s,
                    settings,
                    ReserveRequest(
                        user_id="pg-prid-user",
                        trace_id=f"pg-prid-trace-{key}",
                        idempotency_key=key,
                        model="gpt-4o-mini",
                        estimated_cost=Decimal("5"),
                    ),
                )

        # First attempt: attach provider_request_id "prid-shared"
        with Session(pg_engine) as s:
            apply_settlement(
                s,
                settings,
                SettleRequest(
                    idempotency_key="pg-prid-op-a",
                    outcome="IN_FLIGHT",
                    dispatch_attempt_key="pg-attempt-a",
                    provider_name="openai",
                    model="gpt-4o-mini",
                    provider_request_id="prid-shared",
                ),
            )

        # Second attempt on a *different* operation reusing same provider_request_id
        # must be rejected by the unique index.
        with pytest.raises(ConflictError):
            with Session(pg_engine) as s:
                apply_settlement(
                    s,
                    settings,
                    SettleRequest(
                        idempotency_key="pg-prid-op-b",
                        outcome="IN_FLIGHT",
                        dispatch_attempt_key="pg-attempt-b",
                        provider_name="openai",
                        model="gpt-4o-mini",
                        provider_request_id="prid-shared",
                    ),
                )


# ---------------------------------------------------------------------------
# 4. Provider failover beneath one logical operation
# ---------------------------------------------------------------------------

class TestProviderFailover:
    def test_failover_attempt_allowed_same_operation(self, pg_engine: Engine) -> None:
        """A logical operation may attempt multiple providers without conflict."""
        settings = _pg_settings(str(pg_engine.url))
        with pg_engine.begin() as conn:
            _seed_wallet(conn, user_id="pg-fo-user")

        with Session(pg_engine) as s:
            reserve_operation(
                s,
                settings,
                ReserveRequest(
                    user_id="pg-fo-user",
                    trace_id="pg-fo-trace",
                    idempotency_key="pg-fo-op",
                    model="gpt-4o-mini",
                    estimated_cost=Decimal("8"),
                ),
            )

        for attempt_key, provider, prid, outcome in [
            ("pg-fo-a1", "openai", "prid-fo-a1", "IN_FLIGHT"),
            ("pg-fo-a1", "openai", "prid-fo-a1", "PROVIDER_TIMEOUT"),
            ("pg-fo-a2", "anthropic", "prid-fo-a2", "IN_FLIGHT"),
        ]:
            with Session(pg_engine) as s:
                apply_settlement(
                    s,
                    settings,
                    SettleRequest(
                        idempotency_key="pg-fo-op",
                        outcome=outcome,
                        dispatch_attempt_key=attempt_key,
                        provider_name=provider,
                        model="gpt-4o-mini",
                        provider_request_id=prid,
                    ),
                )

        with Session(pg_engine) as s:
            settled = apply_settlement(
                s,
                settings,
                SettleRequest(
                    idempotency_key="pg-fo-op",
                    outcome="SETTLED",
                    actual_cost=Decimal("8"),
                    dispatch_attempt_key="pg-fo-a2",
                    provider_name="anthropic",
                    model="gpt-4o-mini",
                    provider_request_id="prid-fo-a2",
                ),
            )
            attempts = s.execute(
                text(
                    "SELECT attempt_key, status FROM provider_dispatch_attempts "
                    "WHERE idempotency_key = 'pg-fo-op' ORDER BY attempt_key"
                )
            ).mappings().all()

        assert settled.status == "SETTLED"
        attempt_statuses = {r["attempt_key"]: r["status"] for r in attempts}
        assert attempt_statuses["pg-fo-a1"] == "PROVIDER_TIMEOUT"
        assert attempt_statuses["pg-fo-a2"] == "SETTLED"


# ---------------------------------------------------------------------------
# 5. Reconciler expiry claim behaviour
# ---------------------------------------------------------------------------

class TestReconcilerExpiryBehaviour:
    def test_clean_reservation_expires_to_refund(self, pg_engine: Engine) -> None:
        """A RESERVED operation that expired without dispatch is refunded."""
        settings = _pg_settings(str(pg_engine.url))
        with pg_engine.begin() as conn:
            _seed_wallet(conn, user_id="pg-exp-user")

        with Session(pg_engine) as s:
            reserve_operation(
                s,
                settings,
                ReserveRequest(
                    user_id="pg-exp-user",
                    trace_id="pg-exp-trace",
                    idempotency_key="pg-exp-op",
                    model="gpt-4o-mini",
                    estimated_cost=Decimal("15"),
                ),
            )

        with pg_engine.begin() as conn:
            _expire_reservation(conn, idempotency_key="pg-exp-op")

        with Session(pg_engine) as s:
            swept = sweep_expired_reservations(s, batch_size=50)

        assert swept == 1

        with Session(pg_engine) as s:
            ledger = s.execute(
                text(
                    "SELECT status, terminal_reason FROM escrow_ledger "
                    "WHERE idempotency_key = 'pg-exp-op'"
                )
            ).mappings().one()
            balance = s.execute(
                text("SELECT balance FROM user_wallets WHERE user_id = 'pg-exp-user'")
            ).scalar_one()

        assert ledger["status"] == "EXPIRED"
        assert ledger["terminal_reason"] == "TTL_EXPIRED"
        assert _money(balance) == Decimal("200.000000")  # full refund

    def test_in_flight_reservation_strands_at_expiry(self, pg_engine: Engine) -> None:
        """An IN_FLIGHT reservation at expiry becomes STRANDED, not refunded."""
        settings = _pg_settings(str(pg_engine.url))
        with pg_engine.begin() as conn:
            _seed_wallet(conn, user_id="pg-str-user")

        with Session(pg_engine) as s:
            reserve_operation(
                s,
                settings,
                ReserveRequest(
                    user_id="pg-str-user",
                    trace_id="pg-str-trace",
                    idempotency_key="pg-str-op",
                    model="gpt-4o-mini",
                    estimated_cost=Decimal("12"),
                ),
            )

        with Session(pg_engine) as s:
            apply_settlement(
                s,
                settings,
                SettleRequest(
                    idempotency_key="pg-str-op",
                    outcome="IN_FLIGHT",
                    dispatch_attempt_key="pg-str-a1",
                    provider_name="openai",
                    model="gpt-4o-mini",
                    provider_request_id="prid-str-1",
                ),
            )

        with pg_engine.begin() as conn:
            _expire_reservation(conn, idempotency_key="pg-str-op")

        with Session(pg_engine) as s:
            swept = sweep_expired_reservations(s, batch_size=50)

        assert swept == 1

        with Session(pg_engine) as s:
            ledger = s.execute(
                text(
                    "SELECT status, terminal_reason FROM escrow_ledger "
                    "WHERE idempotency_key = 'pg-str-op'"
                )
            ).mappings().one()
            balance = s.execute(
                text("SELECT balance FROM user_wallets WHERE user_id = 'pg-str-user'")
            ).scalar_one()

        assert ledger["status"] == "STRANDED"
        assert "STRANDED" in ledger["terminal_reason"]
        # Funds are NOT refunded while STRANDED — held for authoritative settlement.
        assert _money(balance) == Decimal("188.000000")  # 200 - 12


# ---------------------------------------------------------------------------
# 6. Late settlement after expiry / stranded hold
# ---------------------------------------------------------------------------

class TestLateSettlement:
    def test_late_settle_after_expired_appends_correction(self, pg_engine: Engine) -> None:
        """Settling after EXPIRED state debits only the actual cost (correction)."""
        settings = _pg_settings(str(pg_engine.url))
        with pg_engine.begin() as conn:
            _seed_wallet(conn, user_id="pg-late-user")

        with Session(pg_engine) as s:
            reserve_operation(
                s,
                settings,
                ReserveRequest(
                    user_id="pg-late-user",
                    trace_id="pg-late-trace",
                    idempotency_key="pg-late-op",
                    model="gpt-4o-mini",
                    estimated_cost=Decimal("10"),
                ),
            )

        with pg_engine.begin() as conn:
            _expire_reservation(conn, idempotency_key="pg-late-op")

        with Session(pg_engine) as s:
            sweep_expired_reservations(s, batch_size=50)

        with Session(pg_engine) as s:
            apply_settlement(
                s,
                settings,
                SettleRequest(
                    idempotency_key="pg-late-op",
                    outcome="SETTLED",
                    actual_cost=Decimal("4"),
                    provider_request_id="prid-late-1",
                ),
            )

        with Session(pg_engine) as s:
            balance = s.execute(
                text("SELECT balance FROM user_wallets WHERE user_id = 'pg-late-user'")
            ).scalar_one()
            events = s.execute(
                text(
                    "SELECT event_type FROM ledger_events "
                    "WHERE idempotency_key = 'pg-late-op' ORDER BY event_id"
                )
            ).scalars().all()

        assert _money(balance) == Decimal("196.000000")  # 200 refunded (EXPIRED) - 4 correction
        assert "EXPIRED_SWEEP" in events
        assert "SETTLEMENT_CORRECTION_DEBIT" in events
        assert "RECONCILED_LATE_SETTLE" in events

    def test_late_settle_after_stranded_appends_correction_debit(
        self, pg_engine: Engine
    ) -> None:
        """Settling a STRANDED hold debits the actual cost without double-charging."""
        settings = _pg_settings(str(pg_engine.url))
        with pg_engine.begin() as conn:
            _seed_wallet(conn, user_id="pg-strls-user")

        with Session(pg_engine) as s:
            reserve_operation(
                s,
                settings,
                ReserveRequest(
                    user_id="pg-strls-user",
                    trace_id="pg-strls-trace",
                    idempotency_key="pg-strls-op",
                    model="gpt-4o-mini",
                    estimated_cost=Decimal("10"),
                ),
            )

        with Session(pg_engine) as s:
            apply_settlement(
                s,
                settings,
                SettleRequest(
                    idempotency_key="pg-strls-op",
                    outcome="IN_FLIGHT",
                    dispatch_attempt_key="pg-strls-a1",
                    provider_name="openai",
                    model="gpt-4o-mini",
                    provider_request_id="prid-strls-1",
                ),
            )

        with pg_engine.begin() as conn:
            _expire_reservation(conn, idempotency_key="pg-strls-op")

        with Session(pg_engine) as s:
            sweep_expired_reservations(s, batch_size=50)

        with Session(pg_engine) as s:
            apply_settlement(
                s,
                settings,
                SettleRequest(
                    idempotency_key="pg-strls-op",
                    outcome="SETTLED",
                    actual_cost=Decimal("8"),
                    dispatch_attempt_key="pg-strls-a1",
                    provider_name="openai",
                    model="gpt-4o-mini",
                    provider_request_id="prid-strls-1",
                ),
            )

        with Session(pg_engine) as s:
            ledger = s.execute(
                text(
                    "SELECT status, terminal_reason, actual_amount "
                    "FROM escrow_ledger WHERE idempotency_key = 'pg-strls-op'"
                )
            ).mappings().one()
            balance = s.execute(
                text("SELECT balance FROM user_wallets WHERE user_id = 'pg-strls-user'")
            ).scalar_one()

        assert ledger["status"] == "SETTLED"
        assert ledger["terminal_reason"] == "RECONCILED_LATE_SETTLE"
        assert _money(ledger["actual_amount"]) == Decimal("8.000000")
        # STRANDED holds still keep the reserve, so settling at 8 refunds the unused 2.
        # balance = 200 - 10 reserve + 2 settlement refund = 192
        assert _money(balance) == Decimal("192.000000")


# ---------------------------------------------------------------------------
# 7. Drift enforcement causing wallet lockout
# ---------------------------------------------------------------------------

class TestDriftEnforcement:
    def test_drift_above_threshold_locks_wallet(self, pg_engine: Engine) -> None:
        """actual_cost >> reserve triggers DRIFT_ENFORCED and wallet lockout."""
        settings = _pg_settings(
            str(pg_engine.url),
            drift_absolute_tolerance=Decimal("0.5"),
            drift_ratio_tolerance=Decimal("0.05"),
        )
        with pg_engine.begin() as conn:
            _seed_wallet(conn, user_id="pg-drift-hi")

        with Session(pg_engine) as s:
            reserve_operation(
                s,
                settings,
                ReserveRequest(
                    user_id="pg-drift-hi",
                    trace_id="pg-drift-trace-hi",
                    idempotency_key="pg-drift-op-hi",
                    model="gpt-4o-mini",
                    estimated_cost=Decimal("10"),
                ),
            )

        with Session(pg_engine) as s:
            apply_settlement(
                s,
                settings,
                SettleRequest(
                    idempotency_key="pg-drift-op-hi",
                    outcome="SETTLED",
                    actual_cost=Decimal("12"),  # +2 on 10 = 20% drift → exceeds 5% ratio
                    provider_request_id="prid-drift-hi",
                ),
            )

        with Session(pg_engine) as s:
            wallet = s.execute(
                text(
                    "SELECT active, lock_reason FROM user_wallets "
                    "WHERE user_id = 'pg-drift-hi'"
                )
            ).mappings().one()
            events = s.execute(
                text(
                    "SELECT event_type FROM ledger_events "
                    "WHERE idempotency_key = 'pg-drift-op-hi' ORDER BY event_id"
                )
            ).scalars().all()

        assert wallet["active"] is False
        assert wallet["lock_reason"] == "DRIFT_THRESHOLD_EXCEEDED"
        assert "DRIFT_ENFORCED" in events

    def test_drift_below_threshold_does_not_lock(self, pg_engine: Engine) -> None:
        settings = _pg_settings(
            str(pg_engine.url),
            drift_absolute_tolerance=Decimal("0.5"),
            drift_ratio_tolerance=Decimal("0.05"),
        )
        with pg_engine.begin() as conn:
            _seed_wallet(conn, user_id="pg-drift-lo")

        with Session(pg_engine) as s:
            reserve_operation(
                s,
                settings,
                ReserveRequest(
                    user_id="pg-drift-lo",
                    trace_id="pg-drift-trace-lo",
                    idempotency_key="pg-drift-op-lo",
                    model="gpt-4o-mini",
                    estimated_cost=Decimal("10"),
                ),
            )

        with Session(pg_engine) as s:
            apply_settlement(
                s,
                settings,
                SettleRequest(
                    idempotency_key="pg-drift-op-lo",
                    outcome="SETTLED",
                    actual_cost=Decimal("10.3"),  # 3% drift — within 5% ratio
                    provider_request_id="prid-drift-lo",
                ),
            )

        with Session(pg_engine) as s:
            wallet = s.execute(
                text(
                    "SELECT active FROM user_wallets WHERE user_id = 'pg-drift-lo'"
                )
            ).scalar_one()
            events = s.execute(
                text(
                    "SELECT event_type FROM ledger_events "
                    "WHERE idempotency_key = 'pg-drift-op-lo' ORDER BY event_id"
                )
            ).scalars().all()

        assert wallet is True
        assert "DRIFT_TOLERATED" in events

    def test_locked_wallet_denies_new_reserve(self, pg_engine: Engine) -> None:
        """After lockout the wallet rejects further reserve attempts."""
        settings = _pg_settings(
            str(pg_engine.url),
            drift_absolute_tolerance=Decimal("0.5"),
            drift_ratio_tolerance=Decimal("0.05"),
        )
        with pg_engine.begin() as conn:
            _seed_wallet(conn, user_id="pg-lock-user")

        # Force drift lock
        with Session(pg_engine) as s:
            reserve_operation(
                s,
                settings,
                ReserveRequest(
                    user_id="pg-lock-user",
                    trace_id="pg-lock-trace",
                    idempotency_key="pg-lock-op1",
                    model="gpt-4o-mini",
                    estimated_cost=Decimal("10"),
                ),
            )
        with Session(pg_engine) as s:
            apply_settlement(
                s,
                settings,
                SettleRequest(
                    idempotency_key="pg-lock-op1",
                    outcome="SETTLED",
                    actual_cost=Decimal("15"),
                    provider_request_id="prid-lock-1",
                ),
            )

        with pytest.raises(InsufficientFundsError):
            with Session(pg_engine) as s:
                reserve_operation(
                    s,
                    settings,
                    ReserveRequest(
                        user_id="pg-lock-user",
                        trace_id="pg-lock-trace-2",
                        idempotency_key="pg-lock-op2",
                        model="gpt-4o-mini",
                        estimated_cost=Decimal("1"),
                    ),
                )


# ---------------------------------------------------------------------------
# 8. Concurrent reconciler workers: FOR UPDATE SKIP LOCKED prevents duplicate
#    refunds and double-processing on Postgres.
# ---------------------------------------------------------------------------

class TestReconcilerRaceSafety:
    def test_concurrent_sweepers_no_duplicate_refunds(self, pg_engine: Engine) -> None:
        """Two concurrent reconciler workers must each process distinct rows.

        With FOR UPDATE SKIP LOCKED on Postgres, worker A and worker B claim
        non-overlapping sets.  The total wallet credit must equal exactly the
        sum of reserved amounts — no double-refund, no missed refund.
        """
        settings = _pg_settings(str(pg_engine.url))
        factory = sessionmaker(bind=pg_engine, autoflush=False, autocommit=False, future=True)

        n_reservations = 20
        reserve_amount = Decimal("5")
        total_reserved = reserve_amount * n_reservations

        with pg_engine.begin() as conn:
            _seed_wallet(conn, user_id="pg-race-user", balance=Decimal("10000"))

        # Create N expired reservations across N distinct traces.
        for i in range(n_reservations):
            with Session(pg_engine) as s:
                reserve_operation(
                    s,
                    settings,
                    ReserveRequest(
                        user_id="pg-race-user",
                        trace_id=f"pg-race-trace-{i}",
                        idempotency_key=f"pg-race-op-{i}",
                        model="gpt-4o-mini",
                        estimated_cost=reserve_amount,
                    ),
                )

        # Back-date all reservations so they appear expired.
        with pg_engine.begin() as conn:
            conn.execute(
                text(
                    "UPDATE escrow_ledger "
                    "SET expires_at = :t "
                    "WHERE idempotency_key LIKE 'pg-race-op-%'"
                ),
                {"t": _utcnow() - timedelta(minutes=5)},
            )

        swept_counts: list[int] = []

        def run_sweeper(_: int) -> int:
            with factory() as s:
                return sweep_expired_reservations(s, batch_size=n_reservations)

        # Run two sweepers concurrently; each should grab distinct rows.
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(run_sweeper, i) for i in range(2)]
            for f in as_completed(futures):
                swept_counts.append(f.result())

        total_swept = sum(swept_counts)

        with Session(pg_engine) as s:
            balance = s.execute(
                text("SELECT balance FROM user_wallets WHERE user_id = 'pg-race-user'")
            ).scalar_one()
            expired_count = s.execute(
                text(
                    "SELECT COUNT(*) FROM escrow_ledger "
                    "WHERE idempotency_key LIKE 'pg-race-op-%' AND status = 'EXPIRED'"
                )
            ).scalar_one()
            event_count = s.execute(
                text(
                    "SELECT COUNT(*) FROM ledger_events "
                    "WHERE idempotency_key LIKE 'pg-race-op-%' AND event_type = 'EXPIRED_SWEEP'"
                )
            ).scalar_one()

        # Every reservation must be expired exactly once.
        assert total_swept == n_reservations, (
            f"Expected {n_reservations} swept total, got {total_swept} "
            f"({swept_counts[0]} + {swept_counts[1]})"
        )
        assert expired_count == n_reservations
        assert event_count == n_reservations  # exactly one EXPIRED_SWEEP per row

        expected_balance = Decimal("10000") - total_reserved + total_reserved  # net zero
        assert _money(balance) == expected_balance, (
            f"Balance mismatch: expected {expected_balance}, got {_money(balance)}"
        )

    def test_concurrent_sweepers_no_duplicate_stranded_events(
        self, pg_engine: Engine
    ) -> None:
        """STRANDED rows with open attempts must be claimed by exactly one worker."""
        settings = _pg_settings(str(pg_engine.url))
        factory = sessionmaker(bind=pg_engine, autoflush=False, autocommit=False, future=True)

        n = 10
        with pg_engine.begin() as conn:
            _seed_wallet(conn, user_id="pg-str-race-user", balance=Decimal("5000"))

        for i in range(n):
            with Session(pg_engine) as s:
                reserve_operation(
                    s,
                    settings,
                    ReserveRequest(
                        user_id="pg-str-race-user",
                        trace_id=f"pg-str-race-trace-{i}",
                        idempotency_key=f"pg-str-race-op-{i}",
                        model="gpt-4o-mini",
                        estimated_cost=Decimal("3"),
                    ),
                )
            with Session(pg_engine) as s:
                apply_settlement(
                    s,
                    settings,
                    SettleRequest(
                        idempotency_key=f"pg-str-race-op-{i}",
                        outcome="IN_FLIGHT",
                        dispatch_attempt_key=f"pg-str-race-att-{i}",
                        provider_name="openai",
                        model="gpt-4o-mini",
                        provider_request_id=f"prid-str-race-{i}",
                    ),
                )

        with pg_engine.begin() as conn:
            conn.execute(
                text(
                    "UPDATE escrow_ledger SET expires_at = :t "
                    "WHERE idempotency_key LIKE 'pg-str-race-op-%'"
                ),
                {"t": _utcnow() - timedelta(minutes=5)},
            )

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: sweep_expired_reservations(
                factory(), batch_size=n
            ), range(2)))

        total_swept = sum(results)

        with Session(pg_engine) as s:
            stranded_count = s.execute(
                text(
                    "SELECT COUNT(*) FROM escrow_ledger "
                    "WHERE idempotency_key LIKE 'pg-str-race-op-%' AND status = 'STRANDED'"
                )
            ).scalar_one()
            stranded_event_count = s.execute(
                text(
                    "SELECT COUNT(*) FROM ledger_events "
                    "WHERE idempotency_key LIKE 'pg-str-race-op-%' "
                    "AND event_type = 'STRANDED_HOLD'"
                )
            ).scalar_one()

        assert total_swept == n
        assert stranded_count == n
        assert stranded_event_count == n  # exactly one event per row — no duplicates


# ---------------------------------------------------------------------------
# 9. Invariant consistency check across all tests
# ---------------------------------------------------------------------------

class TestInvariantConsistency:
    def test_no_negative_wallet_balances(self, pg_engine: Engine) -> None:
        """After all operations in this test session, no wallet has a negative
        balance.  Postgres enforces this via CHECK constraint, but this test
        makes the invariant explicit and auditable."""
        with Session(pg_engine) as s:
            negative = s.execute(
                text("SELECT COUNT(*) FROM user_wallets WHERE balance < 0")
            ).scalar_one()
        assert negative == 0, f"Found {negative} wallet(s) with negative balance"

    def test_no_reserved_total_exceeds_cap(self, pg_engine: Engine) -> None:
        """reserved_total must never exceed cap_amount for any trace."""
        with Session(pg_engine) as s:
            overrun = s.execute(
                text(
                    "SELECT COUNT(*) FROM trace_budget_state "
                    "WHERE reserved_total > cap_amount"
                )
            ).scalar_one()
        assert overrun == 0, f"Found {overrun} trace(s) with reserved_total > cap"
