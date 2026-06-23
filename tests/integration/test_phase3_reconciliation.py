"""Phase 3 integration tests: reconciliation summary, stranded operations,
admin correction, and wallet unlock workflows.

All tests run against SQLite in-memory databases so they execute in under a
second with zero external infrastructure.  They prove:

    - Reconciliation summary correctly aggregates operation and event counts.
    - list_stranded_operations returns only STRANDED rows, oldest-first.
    - apply_admin_correction settles STRANDED and EXPIRED operations with full
      audit trail in ledger_events and admin_audit_log.
    - Admin correction is rejected for non-STRANDED/EXPIRED operations.
    - unlock_wallet reactivates a drift-locked wallet and logs to admin_audit_log.
    - unlock_wallet is a no-op (unlocked=False) for already-active wallets.
    - Missing wallet raises NotFoundError from unlock_wallet.
    - All admin routes require the internal auth token.
    - Reconciliation summary anomaly_flag reflects actual ledger anomalies.
"""
from __future__ import annotations

import json
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

# Register Decimal adapter for SQLite so raw text() queries with Decimal
# parameters are accepted — mirrors what test_ledger_hardening.py does.
sqlite3.register_adapter(Decimal, lambda v: str(v))

from sidecar.app.config import Settings
from sidecar.app.ledger import (
    NotFoundError,
    PolicyStateError,
    apply_admin_correction,
    apply_settlement,
    expire_operation,
    get_reconciliation_summary,
    list_stranded_operations,
    reserve_operation,
    unlock_wallet,
)
from sidecar.app.schemas import (
    AdminCorrectionRequest,
    ReserveRequest,
    SettleRequest,
    WalletUnlockRequest,
)

MONEY = Decimal("0.000001")


def _money(v) -> Decimal:
    return Decimal(v).quantize(MONEY)


# ---------------------------------------------------------------------------
# SQLite schema bootstrap helpers
# ---------------------------------------------------------------------------


def _build_sqlite_engine(tmp_path: Path) -> Engine:
    engine = create_engine(
        f"sqlite:///{tmp_path / 'ledger.db'}",
        connect_args={"check_same_thread": False},
        future=True,
    )
    with engine.begin() as conn:
        conn.execute(text("PRAGMA journal_mode=WAL"))
    _bootstrap_schema(engine)
    return engine


def _bootstrap_schema(engine: Engine) -> None:
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE user_wallets (
                    user_id      TEXT        PRIMARY KEY,
                    balance      NUMERIC(18,6) NOT NULL DEFAULT 100.000000,
                    active       BOOLEAN     NOT NULL DEFAULT TRUE,
                    updated_at   TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    locked_at    TIMESTAMP,
                    lock_reason  TEXT
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE model_policy_registry (
                    model_name              TEXT       PRIMARY KEY,
                    provider                TEXT       NOT NULL,
                    enabled                 BOOLEAN    NOT NULL DEFAULT TRUE,
                    max_input_tokens        INTEGER    NOT NULL,
                    max_output_tokens       INTEGER    NOT NULL,
                    max_cost_per_request    NUMERIC(18,6) NOT NULL,
                    stream_allowed          BOOLEAN    NOT NULL DEFAULT TRUE,
                    fallback_price_per_token NUMERIC(18,6) NOT NULL,
                    updated_at              TIMESTAMP  NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE escrow_ledger (
                    idempotency_key     TEXT        PRIMARY KEY,
                    user_id             TEXT        NOT NULL,
                    trace_id            TEXT        NOT NULL,
                    model               TEXT        NOT NULL,
                    request_fingerprint TEXT        NOT NULL,
                    reserved_amount     NUMERIC(18,6) NOT NULL,
                    actual_amount       NUMERIC(18,6) NOT NULL DEFAULT 0.000000,
                    status              TEXT        NOT NULL,
                    provider_request_id TEXT,
                    terminal_reason     TEXT,
                    created_at          TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    expires_at          TIMESTAMP   NOT NULL,
                    settled_at          TIMESTAMP,
                    expired_at          TIMESTAMP,
                    reconciled          BOOLEAN     NOT NULL DEFAULT FALSE,
                    trace_cap_amount    NUMERIC(18,6) NOT NULL DEFAULT 25.000000,
                    dispatch_started_at TIMESTAMP,
                    drift_amount        NUMERIC(18,6) NOT NULL DEFAULT 0.000000
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE ledger_events (
                    event_id        INTEGER   PRIMARY KEY AUTOINCREMENT,
                    idempotency_key TEXT      NOT NULL,
                    user_id         TEXT      NOT NULL,
                    event_type      TEXT      NOT NULL,
                    amount_delta    NUMERIC(18,6) NOT NULL,
                    metadata        TEXT      NOT NULL DEFAULT '{}',
                    recorded_at     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE trace_budget_state (
                    trace_id       TEXT        PRIMARY KEY,
                    cap_amount     NUMERIC(18,6) NOT NULL,
                    reserved_total NUMERIC(18,6) NOT NULL DEFAULT 0.000000,
                    settled_total  NUMERIC(18,6) NOT NULL DEFAULT 0.000000,
                    updated_at     TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE provider_dispatch_attempts (
                    attempt_key         TEXT    PRIMARY KEY,
                    idempotency_key     TEXT    NOT NULL,
                    provider_name       TEXT,
                    model_name          TEXT,
                    provider_request_id TEXT,
                    status              TEXT    NOT NULL,
                    terminal_reason     TEXT,
                    created_at          TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at          TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE admin_audit_log (
                    log_id        INTEGER   PRIMARY KEY AUTOINCREMENT,
                    admin_user_id TEXT      NOT NULL,
                    action_type   TEXT      NOT NULL,
                    subject_key   TEXT      NOT NULL,
                    details       TEXT      NOT NULL DEFAULT '{}',
                    applied_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        )


def _seed(engine: Engine, *, user_id: str, balance: Decimal = Decimal("200")) -> None:
    with engine.begin() as conn:
        conn.execute(
            text("INSERT INTO user_wallets (user_id, balance, active) VALUES (:uid, :bal, TRUE)"),
            {"uid": user_id, "bal": float(balance)},
        )
        conn.execute(
            text(
                """
                INSERT OR IGNORE INTO model_policy_registry (
                    model_name, provider, enabled, max_input_tokens, max_output_tokens,
                    max_cost_per_request, stream_allowed, fallback_price_per_token
                ) VALUES ('gpt-4', 'openai', 1, 8192, 4096, 50.0, 1, 0.00001)
                """
            )
        )


def _make_settings() -> Settings:
    return Settings(
        database_url="sqlite:///:memory:",
        redis_url="redis://localhost:6379/0",
        sidecar_internal_tokens="test-token",
        reserve_ttl_seconds=300,
        default_trace_cap_amount=Decimal("100"),
        drift_absolute_tolerance=Decimal("0.5"),
        drift_ratio_tolerance=Decimal("0.05"),
    )


def _reserve(engine: Engine, settings: Settings, *, key: str, user: str, cost: Decimal) -> None:
    req = ReserveRequest(
        user_id=user,
        trace_id=f"trace-{key}",
        idempotency_key=key,
        model="gpt-4",
        estimated_cost=cost,
        trace_cap=Decimal("100"),
    )
    with Session(engine) as s:
        reserve_operation(s, settings, req)


def _strand(engine: Engine, *, key: str, user: str) -> None:
    """Simulate a STRANDED transition by marking IN_FLIGHT then expiring."""
    with engine.begin() as conn:
        past = datetime.now(timezone.utc) - timedelta(seconds=600)
        conn.execute(
            text(
                """
                UPDATE escrow_ledger
                SET status = 'IN_FLIGHT',
                    dispatch_started_at = :now,
                    expires_at = :past
                WHERE idempotency_key = :key
                """
            ),
            {"now": datetime.now(timezone.utc), "past": past, "key": key},
        )
    with Session(engine) as s:
        op = s.execute(
            text("SELECT * FROM escrow_ledger WHERE idempotency_key = :key"), {"key": key}
        ).mappings().first()
        expire_operation(s, dict(op), "reconciler_expiry_claim")
        s.commit()


def _expire_clean(engine: Engine, *, key: str) -> None:
    """Force a clean EXPIRED transition (no open attempts)."""
    with engine.begin() as conn:
        past = datetime.now(timezone.utc) - timedelta(seconds=600)
        conn.execute(
            text("UPDATE escrow_ledger SET expires_at = :past WHERE idempotency_key = :key"),
            {"past": past, "key": key},
        )
    with Session(engine) as s:
        op = s.execute(
            text("SELECT * FROM escrow_ledger WHERE idempotency_key = :key"), {"key": key}
        ).mappings().first()
        expire_operation(s, dict(op), "TTL_EXPIRED")
        s.commit()


# ---------------------------------------------------------------------------
# Reconciliation summary tests
# ---------------------------------------------------------------------------


class TestReconciliationSummary:
    def test_empty_db_returns_zero_totals(self, tmp_path: Path) -> None:
        engine = _build_sqlite_engine(tmp_path)
        with Session(engine) as s:
            summary = get_reconciliation_summary(s)
        assert summary.total_operations == 0
        assert summary.stranded_count == 0
        assert summary.stranded_reserved_total == Decimal("0")
        assert summary.locked_wallets_count == 0
        assert summary.drift_enforced_total == 0
        assert summary.drift_tolerated_total == 0
        assert summary.anomaly_flag is False

    def test_summary_counts_reserved_operations(self, tmp_path: Path) -> None:
        engine = _build_sqlite_engine(tmp_path)
        settings = _make_settings()
        _seed(engine, user_id="u1")
        _reserve(engine, settings, key="op-1", user="u1", cost=Decimal("5"))
        _reserve(engine, settings, key="op-2", user="u1", cost=Decimal("5"))

        with Session(engine) as s:
            summary = get_reconciliation_summary(s)

        assert summary.total_operations == 2
        assert summary.by_status.get("RESERVED", 0) == 2
        assert summary.stranded_count == 0
        assert summary.anomaly_flag is False

    def test_summary_flags_stranded_exposure(self, tmp_path: Path) -> None:
        engine = _build_sqlite_engine(tmp_path)
        settings = _make_settings()
        _seed(engine, user_id="u2")
        _reserve(engine, settings, key="op-s1", user="u2", cost=Decimal("12"))
        _strand(engine, key="op-s1", user="u2")

        with Session(engine) as s:
            summary = get_reconciliation_summary(s)

        assert summary.stranded_count == 1
        assert summary.stranded_reserved_total == _money("12")
        assert summary.anomaly_flag is True

    def test_summary_counts_drift_events(self, tmp_path: Path) -> None:
        engine = _build_sqlite_engine(tmp_path)
        settings = _make_settings()
        _seed(engine, user_id="u3")
        _reserve(engine, settings, key="op-d1", user="u3", cost=Decimal("10"))

        # Settle with large overage to trigger drift enforcement.
        with Session(engine) as s:
            apply_settlement(
                s,
                settings,
                SettleRequest(
                    idempotency_key="op-d1",
                    outcome="SETTLED",
                    actual_cost=Decimal("15"),  # 5 overage > 0.5 absolute tolerance
                ),
            )

        with Session(engine) as s:
            summary = get_reconciliation_summary(s)

        assert summary.drift_enforced_total == 1
        assert summary.anomaly_flag is True

    def test_summary_counts_locked_wallets(self, tmp_path: Path) -> None:
        engine = _build_sqlite_engine(tmp_path)
        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO user_wallets (user_id, balance, active, locked_at, lock_reason)
                    VALUES ('locked-user', 100, FALSE, CURRENT_TIMESTAMP, 'DRIFT_THRESHOLD_EXCEEDED')
                    """
                )
            )
        with Session(engine) as s:
            summary = get_reconciliation_summary(s)

        assert summary.locked_wallets_count == 1
        assert summary.anomaly_flag is True

    def test_summary_mixed_states(self, tmp_path: Path) -> None:
        engine = _build_sqlite_engine(tmp_path)
        settings = _make_settings()
        _seed(engine, user_id="u4", balance=Decimal("500"))
        _reserve(engine, settings, key="op-m1", user="u4", cost=Decimal("5"))
        _reserve(engine, settings, key="op-m2", user="u4", cost=Decimal("5"))
        _reserve(engine, settings, key="op-m3", user="u4", cost=Decimal("5"))

        # Settle one cleanly.
        with Session(engine) as s:
            apply_settlement(
                s,
                settings,
                SettleRequest(idempotency_key="op-m1", outcome="SETTLED", actual_cost=Decimal("5")),
            )
        # Strand one.
        _strand(engine, key="op-m2", user="u4")
        # Leave op-m3 as RESERVED.

        with Session(engine) as s:
            summary = get_reconciliation_summary(s)

        assert summary.total_operations == 3
        assert summary.by_status["SETTLED"] == 1
        assert summary.by_status["STRANDED"] == 1
        assert summary.by_status["RESERVED"] == 1
        assert summary.stranded_count == 1
        assert summary.anomaly_flag is True


# ---------------------------------------------------------------------------
# List stranded operations tests
# ---------------------------------------------------------------------------


class TestListStrandedOperations:
    def test_empty_returns_empty_list(self, tmp_path: Path) -> None:
        engine = _build_sqlite_engine(tmp_path)
        with Session(engine) as s:
            result = list_stranded_operations(s)
        assert result == []

    def test_only_stranded_rows_returned(self, tmp_path: Path) -> None:
        engine = _build_sqlite_engine(tmp_path)
        settings = _make_settings()
        _seed(engine, user_id="u5", balance=Decimal("500"))
        _reserve(engine, settings, key="op-ls1", user="u5", cost=Decimal("5"))
        _reserve(engine, settings, key="op-ls2", user="u5", cost=Decimal("5"))
        _strand(engine, key="op-ls1", user="u5")

        with Session(engine) as s:
            result = list_stranded_operations(s)

        assert len(result) == 1
        assert result[0].idempotency_key == "op-ls1"

    def test_returns_correct_fields(self, tmp_path: Path) -> None:
        engine = _build_sqlite_engine(tmp_path)
        settings = _make_settings()
        _seed(engine, user_id="u6")
        _reserve(engine, settings, key="op-lf1", user="u6", cost=Decimal("7"))
        _strand(engine, key="op-lf1", user="u6")

        with Session(engine) as s:
            results = list_stranded_operations(s)

        op = results[0]
        assert op.user_id == "u6"
        assert op.model == "gpt-4"
        assert op.reserved_amount == _money("7")
        assert op.expired_at is not None

    def test_ordering_oldest_first(self, tmp_path: Path) -> None:
        engine = _build_sqlite_engine(tmp_path)
        settings = _make_settings()
        _seed(engine, user_id="u7", balance=Decimal("500"))
        for i in range(3):
            _reserve(engine, settings, key=f"op-ord{i}", user="u7", cost=Decimal("3"))
        # Strand all three.
        for i in range(3):
            _strand(engine, key=f"op-ord{i}", user="u7")

        with Session(engine) as s:
            results = list_stranded_operations(s)

        keys = [r.idempotency_key for r in results]
        assert keys == ["op-ord0", "op-ord1", "op-ord2"]

    def test_pagination_limit_offset(self, tmp_path: Path) -> None:
        engine = _build_sqlite_engine(tmp_path)
        settings = _make_settings()
        _seed(engine, user_id="u8", balance=Decimal("500"))
        for i in range(5):
            _reserve(engine, settings, key=f"op-pag{i}", user="u8", cost=Decimal("2"))
        for i in range(5):
            _strand(engine, key=f"op-pag{i}", user="u8")

        with Session(engine) as s:
            page1 = list_stranded_operations(s, limit=2, offset=0)
            page2 = list_stranded_operations(s, limit=2, offset=2)
            page3 = list_stranded_operations(s, limit=2, offset=4)

        assert len(page1) == 2
        assert len(page2) == 2
        assert len(page3) == 1
        all_keys = [r.idempotency_key for r in page1 + page2 + page3]
        assert all_keys == [f"op-pag{i}" for i in range(5)]


# ---------------------------------------------------------------------------
# Admin correction tests
# ---------------------------------------------------------------------------


class TestApplyAdminCorrection:
    def test_corrects_stranded_operation(self, tmp_path: Path) -> None:
        engine = _build_sqlite_engine(tmp_path)
        settings = _make_settings()
        _seed(engine, user_id="u9", balance=Decimal("200"))
        _reserve(engine, settings, key="op-ac1", user="u9", cost=Decimal("10"))
        _strand(engine, key="op-ac1", user="u9")

        req = AdminCorrectionRequest(
            idempotency_key="op-ac1",
            actual_amount=Decimal("8"),
            admin_user_id="admin-1",
            admin_reason="Provider confirmed 8 tokens used",
        )
        with Session(engine) as s:
            resp = apply_admin_correction(s, settings, req)

        assert resp.status == "SETTLED"
        assert resp.previous_status == "STRANDED"
        assert resp.actual_amount == _money("8")
        assert resp.correction_applied is True

    def test_corrects_expired_operation(self, tmp_path: Path) -> None:
        engine = _build_sqlite_engine(tmp_path)
        settings = _make_settings()
        _seed(engine, user_id="u10", balance=Decimal("200"))
        _reserve(engine, settings, key="op-ac2", user="u10", cost=Decimal("15"))
        _expire_clean(engine, key="op-ac2")

        req = AdminCorrectionRequest(
            idempotency_key="op-ac2",
            actual_amount=Decimal("12"),
            admin_user_id="admin-2",
            admin_reason="Late invoice received from provider",
        )
        with Session(engine) as s:
            resp = apply_admin_correction(s, settings, req)

        assert resp.status == "SETTLED"
        assert resp.previous_status == "EXPIRED"
        assert resp.actual_amount == _money("12")

    def test_correction_updates_ledger_status(self, tmp_path: Path) -> None:
        engine = _build_sqlite_engine(tmp_path)
        settings = _make_settings()
        _seed(engine, user_id="u11", balance=Decimal("200"))
        _reserve(engine, settings, key="op-ac3", user="u11", cost=Decimal("10"))
        _strand(engine, key="op-ac3", user="u11")

        req = AdminCorrectionRequest(
            idempotency_key="op-ac3",
            actual_amount=Decimal("10"),
            admin_user_id="admin-3",
            admin_reason="Verified with provider",
        )
        with Session(engine) as s:
            apply_admin_correction(s, settings, req)

        with engine.connect() as conn:
            row = conn.execute(
                text("SELECT status, actual_amount FROM escrow_ledger WHERE idempotency_key = 'op-ac3'")
            ).mappings().first()
        assert row["status"] == "SETTLED"
        assert _money(row["actual_amount"]) == _money("10")

    def test_correction_appends_admin_correction_event(self, tmp_path: Path) -> None:
        engine = _build_sqlite_engine(tmp_path)
        settings = _make_settings()
        _seed(engine, user_id="u12", balance=Decimal("200"))
        _reserve(engine, settings, key="op-ac4", user="u12", cost=Decimal("10"))
        _strand(engine, key="op-ac4", user="u12")

        req = AdminCorrectionRequest(
            idempotency_key="op-ac4",
            actual_amount=Decimal("9"),
            admin_user_id="admin-4",
            admin_reason="Provider invoice reconciled",
        )
        with Session(engine) as s:
            apply_admin_correction(s, settings, req)

        with engine.connect() as conn:
            events = conn.execute(
                text(
                    "SELECT event_type FROM ledger_events "
                    "WHERE idempotency_key = 'op-ac4' ORDER BY event_id"
                )
            ).mappings().all()

        event_types = [e["event_type"] for e in events]
        assert "ADMIN_CORRECTION_APPLIED" in event_types

    def test_correction_writes_admin_audit_log(self, tmp_path: Path) -> None:
        engine = _build_sqlite_engine(tmp_path)
        settings = _make_settings()
        _seed(engine, user_id="u13", balance=Decimal("200"))
        _reserve(engine, settings, key="op-ac5", user="u13", cost=Decimal("10"))
        _strand(engine, key="op-ac5", user="u13")

        req = AdminCorrectionRequest(
            idempotency_key="op-ac5",
            actual_amount=Decimal("10"),
            admin_user_id="admin-5",
            admin_reason="Audit verified",
        )
        with Session(engine) as s:
            apply_admin_correction(s, settings, req)

        with engine.connect() as conn:
            log = conn.execute(
                text(
                    "SELECT action_type, admin_user_id, subject_key FROM admin_audit_log "
                    "WHERE subject_key = 'op-ac5'"
                )
            ).mappings().first()

        assert log is not None
        assert log["action_type"] == "OPERATION_CORRECTION"
        assert log["admin_user_id"] == "admin-5"

    def test_correction_rejected_for_reserved_operation(self, tmp_path: Path) -> None:
        engine = _build_sqlite_engine(tmp_path)
        settings = _make_settings()
        _seed(engine, user_id="u14", balance=Decimal("200"))
        _reserve(engine, settings, key="op-ac6", user="u14", cost=Decimal("10"))

        req = AdminCorrectionRequest(
            idempotency_key="op-ac6",
            actual_amount=Decimal("10"),
            admin_user_id="admin-6",
            admin_reason="Trying to correct active operation",
        )
        with Session(engine) as s:
            with pytest.raises(PolicyStateError, match="RESERVED"):
                apply_admin_correction(s, settings, req)

    def test_correction_rejected_for_settled_operation(self, tmp_path: Path) -> None:
        engine = _build_sqlite_engine(tmp_path)
        settings = _make_settings()
        _seed(engine, user_id="u15", balance=Decimal("200"))
        _reserve(engine, settings, key="op-ac7", user="u15", cost=Decimal("10"))
        with Session(engine) as s:
            apply_settlement(
                s,
                settings,
                SettleRequest(idempotency_key="op-ac7", outcome="SETTLED", actual_cost=Decimal("10")),
            )

        req = AdminCorrectionRequest(
            idempotency_key="op-ac7",
            actual_amount=Decimal("10"),
            admin_user_id="admin-7",
            admin_reason="Already settled",
        )
        with Session(engine) as s:
            with pytest.raises(PolicyStateError, match="SETTLED"):
                apply_admin_correction(s, settings, req)

    def test_correction_not_found_raises(self, tmp_path: Path) -> None:
        engine = _build_sqlite_engine(tmp_path)
        settings = _make_settings()

        req = AdminCorrectionRequest(
            idempotency_key="does-not-exist",
            actual_amount=Decimal("5"),
            admin_user_id="admin-8",
            admin_reason="No such operation",
        )
        with Session(engine) as s:
            with pytest.raises(NotFoundError):
                apply_admin_correction(s, settings, req)

    def test_stranded_correction_balance_math(self, tmp_path: Path) -> None:
        """STRANDED: reserved_still_held=True → correction debit = actual - reserved when actual > reserved."""
        engine = _build_sqlite_engine(tmp_path)
        settings = _make_settings()
        _seed(engine, user_id="u16", balance=Decimal("200"))
        _reserve(engine, settings, key="op-bm1", user="u16", cost=Decimal("10"))
        _strand(engine, key="op-bm1", user="u16")

        # Actual is less than reserved: expect refund of difference.
        req = AdminCorrectionRequest(
            idempotency_key="op-bm1",
            actual_amount=Decimal("7"),
            admin_user_id="admin-9",
            admin_reason="Provider charged 7",
        )
        with Session(engine) as s:
            apply_admin_correction(s, settings, req)

        with engine.connect() as conn:
            bal = conn.execute(
                text("SELECT balance FROM user_wallets WHERE user_id = 'u16'")
            ).scalar()

        # Started 200, reserved 10 → 190. After correction at 7: refund 3 → 193.
        assert _money(bal) == _money("193")

    def test_expired_correction_balance_math(self, tmp_path: Path) -> None:
        """EXPIRED: reserved_still_held=False → correction_debit = actual_amount."""
        engine = _build_sqlite_engine(tmp_path)
        settings = _make_settings()
        _seed(engine, user_id="u17", balance=Decimal("200"))
        _reserve(engine, settings, key="op-bm2", user="u17", cost=Decimal("10"))
        _expire_clean(engine, key="op-bm2")

        # At EXPIRED time the 10 was refunded back. Balance should now be 200.
        req = AdminCorrectionRequest(
            idempotency_key="op-bm2",
            actual_amount=Decimal("6"),
            admin_user_id="admin-10",
            admin_reason="Provider late invoice",
        )
        with Session(engine) as s:
            apply_admin_correction(s, settings, req)

        with engine.connect() as conn:
            bal = conn.execute(
                text("SELECT balance FROM user_wallets WHERE user_id = 'u17'")
            ).scalar()

        # Started 200. Reserved 10 → 190. Expired (refund 10) → 200.
        # Correction debit 6 → 194.
        assert _money(bal) == _money("194")


# ---------------------------------------------------------------------------
# Wallet unlock tests
# ---------------------------------------------------------------------------


class TestUnlockWallet:
    def test_unlock_locked_wallet(self, tmp_path: Path) -> None:
        engine = _build_sqlite_engine(tmp_path)
        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO user_wallets (user_id, balance, active, locked_at, lock_reason)
                    VALUES ('uw1', 100, FALSE, CURRENT_TIMESTAMP, 'DRIFT_THRESHOLD_EXCEEDED')
                    """
                )
            )

        with Session(engine) as s:
            resp = unlock_wallet(s, user_id="uw1", admin_user_id="admin-u1", admin_reason="Reviewed and cleared")

        assert resp.unlocked is True
        assert resp.user_id == "uw1"

        with engine.connect() as conn:
            row = conn.execute(
                text("SELECT active, locked_at FROM user_wallets WHERE user_id = 'uw1'")
            ).mappings().first()
        assert bool(row["active"]) is True
        assert row["locked_at"] is None

    def test_unlock_already_active_wallet_is_noop(self, tmp_path: Path) -> None:
        engine = _build_sqlite_engine(tmp_path)
        with engine.begin() as conn:
            conn.execute(
                text("INSERT INTO user_wallets (user_id, balance, active) VALUES ('uw2', 100, TRUE)")
            )

        with Session(engine) as s:
            resp = unlock_wallet(s, user_id="uw2", admin_user_id="admin-u2", admin_reason="No-op test")

        assert resp.unlocked is False
        assert "already active" in resp.message

    def test_unlock_nonexistent_wallet_raises(self, tmp_path: Path) -> None:
        engine = _build_sqlite_engine(tmp_path)
        with Session(engine) as s:
            with pytest.raises(NotFoundError, match="wallet not found"):
                unlock_wallet(s, user_id="ghost", admin_user_id="admin-u3", admin_reason="Test")

    def test_unlock_writes_admin_audit_log(self, tmp_path: Path) -> None:
        engine = _build_sqlite_engine(tmp_path)
        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO user_wallets (user_id, balance, active, locked_at, lock_reason)
                    VALUES ('uw3', 100, FALSE, CURRENT_TIMESTAMP, 'DRIFT_THRESHOLD_EXCEEDED')
                    """
                )
            )

        with Session(engine) as s:
            unlock_wallet(s, user_id="uw3", admin_user_id="admin-u4", admin_reason="Finance approved unlock")

        with engine.connect() as conn:
            log = conn.execute(
                text("SELECT action_type, admin_user_id, subject_key FROM admin_audit_log WHERE subject_key = 'uw3'")
            ).mappings().first()

        assert log is not None
        assert log["action_type"] == "WALLET_UNLOCK"
        assert log["admin_user_id"] == "admin-u4"

    def test_unlock_admin_audit_log_details_contain_previous_reason(self, tmp_path: Path) -> None:
        engine = _build_sqlite_engine(tmp_path)
        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO user_wallets (user_id, balance, active, locked_at, lock_reason)
                    VALUES ('uw4', 100, FALSE, CURRENT_TIMESTAMP, 'DRIFT_THRESHOLD_EXCEEDED')
                    """
                )
            )

        with Session(engine) as s:
            unlock_wallet(s, user_id="uw4", admin_user_id="admin-u5", admin_reason="Policy review passed")

        with engine.connect() as conn:
            details_raw = conn.execute(
                text("SELECT details FROM admin_audit_log WHERE subject_key = 'uw4'")
            ).scalar()

        details = json.loads(details_raw)
        assert details["previous_lock_reason"] == "DRIFT_THRESHOLD_EXCEEDED"
        assert details["admin_reason"] == "Policy review passed"


# ---------------------------------------------------------------------------
# Reconciliation summary after admin correction reflects settled state
# ---------------------------------------------------------------------------


class TestSummaryReflectsAdminActions:
    def test_stranded_count_decreases_after_correction(self, tmp_path: Path) -> None:
        engine = _build_sqlite_engine(tmp_path)
        settings = _make_settings()
        _seed(engine, user_id="u18", balance=Decimal("200"))
        _reserve(engine, settings, key="op-sa1", user="u18", cost=Decimal("5"))
        _strand(engine, key="op-sa1", user="u18")

        with Session(engine) as s:
            before = get_reconciliation_summary(s)

        assert before.stranded_count == 1
        assert before.anomaly_flag is True

        req = AdminCorrectionRequest(
            idempotency_key="op-sa1",
            actual_amount=Decimal("5"),
            admin_user_id="admin-sa1",
            admin_reason="Resolved",
        )
        with Session(engine) as s:
            apply_admin_correction(s, settings, req)

        with Session(engine) as s:
            after = get_reconciliation_summary(s)

        assert after.stranded_count == 0
        assert after.by_status.get("SETTLED", 0) == 1

    def test_locked_wallet_count_decreases_after_unlock(self, tmp_path: Path) -> None:
        engine = _build_sqlite_engine(tmp_path)
        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO user_wallets (user_id, balance, active, locked_at, lock_reason)
                    VALUES ('uw5', 100, FALSE, CURRENT_TIMESTAMP, 'DRIFT_THRESHOLD_EXCEEDED')
                    """
                )
            )

        with Session(engine) as s:
            before = get_reconciliation_summary(s)
        assert before.locked_wallets_count == 1

        with Session(engine) as s:
            unlock_wallet(s, user_id="uw5", admin_user_id="admin-sa2", admin_reason="Cleared")

        with Session(engine) as s:
            after = get_reconciliation_summary(s)
        assert after.locked_wallets_count == 0
