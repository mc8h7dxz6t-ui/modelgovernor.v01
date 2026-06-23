"""Shared pytest fixtures for Postgres-backed integration tests."""
from __future__ import annotations

import os
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from tests.support.pg_migrations import apply_migrations_to_engine

REPO_ROOT = Path(__file__).resolve().parents[2]
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
]

_TRUNCATE_TABLES = [
    "ledger_events",
    "provider_dispatch_attempts",
    "escrow_ledger",
    "trace_budget_state",
    "user_wallets",
]


@pytest.fixture(scope="session")
def pg_engine() -> Engine:
    pg_url = os.environ.get("POSTGRES_TEST_URL")
    if not pg_url:
        pytest.skip(
            "POSTGRES_TEST_URL is not set — Postgres vigorous tests skipped. "
            "Set POSTGRES_TEST_URL=postgresql://user:pass@host:port/dbname "
            "or run `docker compose -f docker-compose.test.yml up -d` first."
        )
    engine = create_engine(pg_url, future=True)
    _apply_migrations(engine)
    yield engine
    engine.dispose()


def _apply_migrations(engine: Engine) -> None:
    apply_migrations_to_engine(engine, MIGRATIONS_DIR, _MIGRATION_FILES)


@pytest.fixture
def clean_pg_tables(pg_engine: Engine) -> None:
    with pg_engine.begin() as conn:
        for table in _TRUNCATE_TABLES:
            conn.execute(text(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE"))
