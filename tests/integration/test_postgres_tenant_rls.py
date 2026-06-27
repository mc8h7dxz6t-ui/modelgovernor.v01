"""Postgres RLS cross-tenant isolation tests (requires POSTGRES_TEST_URL)."""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from tests.support.pg_migrations import apply_migrations_to_engine

REPO_ROOT = __import__("pathlib").Path(__file__).resolve().parents[2]
MIGRATIONS_DIR = REPO_ROOT / "migrations"

_MIGRATION_FILES = [
    "0001_init.sql",
    "0002_seed_model_policy.sql",
    "0003_harden_ledger_constraints.sql",
    "0004_ledger_control_plane_hardening.sql",
    "0005_invariant_constraints.sql",
    "0006_execution_attribution_guardrails.sql",
    "0007_wallet_nonnegative_backstop.sql",
    "0008_micro_token_precision.sql",
    "0009_ledger_hash_chain.sql",
    "0010_admin_audit_log.sql",
    "0011_ledger_chain_anchors.sql",
    "0013_tenant_rls.sql",
]


def _pg_url() -> str:
    url = os.environ.get("POSTGRES_TEST_URL")
    if not url:
        pytest.skip("POSTGRES_TEST_URL not set")
    return url


@pytest.fixture(scope="module")
def rls_engine() -> Engine:
    engine = create_engine(_pg_url(), future=True)
    apply_migrations_to_engine(engine, MIGRATIONS_DIR, _MIGRATION_FILES)
    with engine.begin() as conn:
        conn.execute(text("GRANT governor_app TO CURRENT_USER"))
    yield engine
    engine.dispose()


def _seed_escrow_row(conn, *, tenant_id: str, idempotency_key: str) -> None:
    now = datetime.now(timezone.utc)
    expires = now + timedelta(minutes=5)
    conn.execute(
        text(
            """
            INSERT INTO escrow_ledger (
                idempotency_key, tenant_id, user_id, session_id, agent_run_id,
                workflow_step, policy_version, trace_id, model, request_fingerprint,
                reserved_amount, actual_amount, status, terminal_reason,
                trace_cap_amount, created_at, expires_at
            ) VALUES (
                :idempotency_key, :tenant_id, 'user-1', 'sess-1', 'agent-1',
                'step-1', 'v1', 'trace-1', 'gpt-4o-mini', 'fp',
                10.000000, 0.000000, 'RESERVED', 'RESERVE_CREATED',
                25.000000, :created_at, :expires_at
            )
            ON CONFLICT (idempotency_key) DO NOTHING
            """
        ),
        {
            "idempotency_key": idempotency_key,
            "tenant_id": tenant_id,
            "created_at": now,
            "expires_at": expires,
        },
    )


def test_rls_escrow_isolation_between_tenants(rls_engine: Engine) -> None:
    with rls_engine.begin() as conn:
        conn.execute(text("TRUNCATE escrow_ledger RESTART IDENTITY CASCADE"))
        _seed_escrow_row(conn, tenant_id="tenant-a", idempotency_key="op-a")
        _seed_escrow_row(conn, tenant_id="tenant-b", idempotency_key="op-b")

    with rls_engine.connect() as conn:
        conn.execute(text("SET ROLE governor_app"))
        conn.execute(text("SELECT set_config('app.current_tenant_id', 'tenant-a', true)"))
        rows = conn.execute(text("SELECT idempotency_key FROM escrow_ledger")).fetchall()
        assert [row[0] for row in rows] == ["op-a"]
        conn.execute(text("RESET ALL"))
        conn.execute(text("SELECT set_config('app.current_tenant_id', 'tenant-b', true)"))
        rows = conn.execute(text("SELECT idempotency_key FROM escrow_ledger")).fetchall()
        assert [row[0] for row in rows] == ["op-b"]
        conn.execute(text("RESET ROLE"))


def test_rls_denies_rows_when_session_tenant_missing(rls_engine: Engine) -> None:
    with rls_engine.begin() as conn:
        conn.execute(text("TRUNCATE escrow_ledger RESTART IDENTITY CASCADE"))
        _seed_escrow_row(conn, tenant_id="tenant-a", idempotency_key="op-a")

    with rls_engine.connect() as conn:
        conn.execute(text("SET ROLE governor_app"))
        rows = conn.execute(text("SELECT idempotency_key FROM escrow_ledger")).fetchall()
        assert rows == []
        conn.execute(text("RESET ROLE"))
