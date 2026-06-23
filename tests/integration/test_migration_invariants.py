"""Migration and DB-level invariant constraint tests."""
from __future__ import annotations

import os
from pathlib import Path

import pytest
from sqlalchemy import text

REPO_ROOT = Path(__file__).resolve().parents[2]
MIGRATIONS_DIR = REPO_ROOT / "migrations"


def test_invariant_migration_file_present() -> None:
    migration = MIGRATIONS_DIR / "0005_invariant_constraints.sql"
    assert migration.exists()
    body = migration.read_text(encoding="utf-8")
    assert "trace_budget_reserved_within_cap" in body
    assert "ledger_events_one_expired_sweep_per_op" in body

    wallet_backstop = MIGRATIONS_DIR / "0007_wallet_nonnegative_backstop.sql"
    assert wallet_backstop.exists()
    assert "user_wallets_nonnegative_balance" in wallet_backstop.read_text(encoding="utf-8")


@pytest.mark.skipif(not os.getenv("POSTGRES_TEST_URL"), reason="POSTGRES_TEST_URL not set")
def test_postgres_trace_cap_check_constraint(pg_engine) -> None:
    with pg_engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO trace_budget_state (trace_id, cap_amount, reserved_total, settled_total)
                VALUES ('cap-test', 10, 5, 0)
                ON CONFLICT (trace_id) DO NOTHING
                """
            )
        )
        with pytest.raises(Exception):
            conn.execute(
                text(
                    "UPDATE trace_budget_state SET reserved_total = 15 WHERE trace_id = 'cap-test'"
                )
            )


@pytest.mark.skipif(not os.getenv("POSTGRES_TEST_URL"), reason="POSTGRES_TEST_URL not set")
def test_postgres_unique_expired_sweep_index(pg_engine) -> None:
    with pg_engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO user_wallets (user_id, balance, active)
                VALUES ('inv-user', 100, TRUE)
                ON CONFLICT (user_id) DO NOTHING
                """
            )
        )
        conn.execute(
            text(
                """
                INSERT INTO escrow_ledger (
                    idempotency_key, user_id, trace_id, model, request_fingerprint,
                    reserved_amount, actual_amount, status, terminal_reason,
                    trace_cap_amount, created_at, expires_at
                ) VALUES (
                    'inv-op', 'inv-user', 'inv-trace', 'gpt-4o-mini', 'fp',
                    5, 0, 'EXPIRED', 'TTL_EXPIRED', 25,
                    CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                )
                ON CONFLICT (idempotency_key) DO NOTHING
                """
            )
        )
        conn.execute(
            text(
                """
                INSERT INTO ledger_events (idempotency_key, user_id, event_type, amount_delta, metadata)
                VALUES ('inv-op', 'inv-user', 'EXPIRED_SWEEP', 5, '{}')
                """
            )
        )
        with pytest.raises(Exception):
            conn.execute(
                text(
                    """
                    INSERT INTO ledger_events (idempotency_key, user_id, event_type, amount_delta, metadata)
                    VALUES ('inv-op', 'inv-user', 'EXPIRED_SWEEP', 5, '{}')
                    """
                )
            )
