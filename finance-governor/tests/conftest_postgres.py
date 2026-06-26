"""Postgres-backed fixtures for Finance Governor spine (Tier 2)."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

REPO_ROOT = Path(__file__).resolve().parents[2]
FG_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tests.support.pg_migrations import apply_migrations_to_engine

MIGRATIONS_DIR = FG_ROOT / "migrations"
_MIGRATION_FILES = [
    "0001_fg_spine_init.sql",
    "0002_fg_ledger_chain_anchors.sql",
]

_TRUNCATE_TABLES = [
    "decision_events",
    "commit_escrow_ledger",
    "governance_crystals",
    "guardrail_incidents",
    "platform_action_attempts",
    "exposure_budget_state",
    "ledger_chain_anchors",
]


@pytest.fixture(scope="session")
def fg_pg_engine() -> Engine:
    pg_url = os.environ.get("FG_POSTGRES_TEST_URL") or os.environ.get("POSTGRES_TEST_URL")
    if not pg_url:
        pytest.skip(
            "FG_POSTGRES_TEST_URL not set — start finance-governor/docker-compose.fg-test.yml "
            "and export FG_POSTGRES_TEST_URL=postgresql+psycopg://postgres:postgres@localhost:5436/financegovernor_test"
        )
    engine = create_engine(pg_url, future=True)
    apply_migrations_to_engine(engine, MIGRATIONS_DIR, _MIGRATION_FILES)
    yield engine
    engine.dispose()


@pytest.fixture
def clean_fg_pg_tables(fg_pg_engine: Engine) -> None:
    with fg_pg_engine.begin() as conn:
        for table in _TRUNCATE_TABLES:
            conn.execute(text(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE"))
        conn.execute(
            text(
                """
                UPDATE account_ledgers
                SET balance = 100000000.000000000000, active = TRUE, lock_reason = NULL
                WHERE account_id = 'desk-default' AND ledger_type = 'exposure'
                """
            )
        )
