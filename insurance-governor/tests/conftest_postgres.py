"""Postgres fixtures for Insurance Governor integration tests."""
from __future__ import annotations

import os
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from support.ig_migrations import apply_ig_migrations

ROOT = Path(__file__).resolve().parents[1]

_TRUNCATE = [
    "claim_events",
    "claim_escrow_ledger",
    "governance_crystals",
    "claim_chain_anchors",
    "admin_audit_log",
    "guardrail_incidents",
    "aggregate_limit_state",
    "payment_idempotency",
    "claim_commitments",
    "oracle_feed_cache",
]


def _apply_migrations(engine: Engine) -> None:
    apply_ig_migrations(engine)


@pytest.fixture(scope="session")
def pg_engine() -> Engine:
    url = os.getenv("POSTGRES_TEST_URL")
    if not url:
        pytest.skip("POSTGRES_TEST_URL not set")
    engine = create_engine(url, future=True)
    _apply_migrations(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def clean_pg_tables(pg_engine: Engine) -> None:
    with pg_engine.begin() as conn:
        for table in _TRUNCATE:
            conn.execute(text(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE"))
        conn.execute(
            text(
                """
                UPDATE reserve_ledgers
                SET balance = 100000000.000000000000, active = TRUE
                WHERE account_id = 'carrier-default' AND ledger_type = 'case'
                """
            )
        )
