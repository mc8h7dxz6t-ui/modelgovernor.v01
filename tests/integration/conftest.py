"""Shared pytest fixtures for Postgres-backed integration tests."""
from __future__ import annotations

import os
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

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
    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        for filename in _MIGRATION_FILES:
            sql = (MIGRATIONS_DIR / filename).read_text(encoding="utf-8")
            for statement in _iter_pg_sql_statements(sql):
                conn.execute(text(statement))


def _iter_pg_sql_statements(sql: str):
    """Split SQL on semicolons outside PostgreSQL dollar-quoted blocks."""
    statements: list[str] = []
    buf: list[str] = []
    i = 0
    n = len(sql)
    in_dollar = False
    dollar_tag = ""

    while i < n:
        if not in_dollar and sql[i] == "$":
            j = i + 1
            while j < n and (sql[j].isalnum() or sql[j] == "_"):
                j += 1
            if j < n and sql[j] == "$":
                dollar_tag = sql[i : j + 1]
                in_dollar = True
                buf.append(dollar_tag)
                i = j + 1
                continue
        if in_dollar and sql.startswith(dollar_tag, i):
            buf.append(dollar_tag)
            i += len(dollar_tag)
            in_dollar = False
            dollar_tag = ""
            continue
        if not in_dollar and sql[i] == ";":
            stmt = "".join(buf).strip()
            if stmt:
                statements.append(stmt)
            buf = []
            i += 1
            continue
        buf.append(sql[i])
        i += 1

    tail = "".join(buf).strip()
    if tail:
        statements.append(tail)
    return statements


@pytest.fixture
def clean_pg_tables(pg_engine: Engine) -> None:
    with pg_engine.begin() as conn:
        for table in _TRUNCATE_TABLES:
            conn.execute(text(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE"))
