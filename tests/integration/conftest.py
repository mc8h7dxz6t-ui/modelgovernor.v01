"""Shared pytest fixtures for the institutional-grade integration test suite.

When ``POSTGRES_TEST_URL`` is set in the environment the session-scoped
``pg_engine`` fixture applies all four migrations against a real Postgres
instance and provides a clean, fully-migrated engine to every test that
requests it.  Tests that need Postgres but find the env-var absent are
automatically skipped with a descriptive message.

Example::

    POSTGRES_TEST_URL=******localhost:5432/mg_test \
        pytest tests/integration/test_postgres_vigorous.py -v

The ``clean_pg_tables`` fixture (autouse within the vigorous-test module)
truncates all ledger tables between individual test functions so each test
starts from a known state.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

REPO_ROOT = Path(__file__).resolve().parents[2]
MIGRATIONS_DIR = REPO_ROOT / "migrations"

# Ordered migration files to apply for a full schema.
_MIGRATION_FILES = [
    "0001_init.sql",
    "0002_seed_model_policy.sql",
    "0003_harden_ledger_constraints.sql",
    "0004_ledger_control_plane_hardening.sql",
]

_TRUNCATE_TABLES = [
    "ledger_events",
    "provider_dispatch_attempts",
    "escrow_ledger",
    "trace_budget_state",
    "user_wallets",
]

# model_policy_registry rows are inserted by migration 0002; keep them across
# tests to avoid FK violations from escrow_ledger.model.


@pytest.fixture(scope="session")
def pg_engine() -> Engine:
    """Session-scoped Postgres engine with all migrations applied.

    Skips the entire session if ``POSTGRES_TEST_URL`` is not set.
    """
    pg_url = os.environ.get("POSTGRES_TEST_URL")
    if not pg_url:
        pytest.skip(
            "POSTGRES_TEST_URL is not set — Postgres vigorous tests skipped. "
            "Set POSTGRES_TEST_URL=******host:port/dbname "
            "or run `docker-compose -f docker-compose.test.yml up -d` first."
        )
    engine = create_engine(pg_url, future=True)
    _apply_migrations(engine)
    yield engine
    engine.dispose()


def _apply_migrations(engine: Engine) -> None:
    """Apply all migration SQL files in order against *engine*."""
    with engine.begin() as conn:
        for filename in _MIGRATION_FILES:
            sql = (MIGRATIONS_DIR / filename).read_text()
            # Split on semicolons, skip empty statements, execute individually
            # so that DDL auto-commits work correctly with psycopg 3.
            for statement in sql.split(";"):
                stripped = statement.strip()
                if stripped:
                    try:
                        conn.execute(text(stripped))
                    except Exception:
                        # Some statements are idempotent (IF NOT EXISTS / ON
                        # CONFLICT DO NOTHING) — re-raise only unexpected errors.
                        raise


@pytest.fixture
def clean_pg_tables(pg_engine: Engine) -> None:
    """Truncate all mutable ledger tables before each test."""
    with pg_engine.begin() as conn:
        for table in _TRUNCATE_TABLES:
            conn.execute(text(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE"))
