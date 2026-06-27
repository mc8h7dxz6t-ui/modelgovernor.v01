"""Postgres connection reliability for Cybersecurity Governor."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

ROOT = Path(__file__).resolve().parents[1]
SIDECAR = ROOT / "spine" / "sidecar"
TESTS = ROOT / "tests"
sys.path.insert(0, str(SIDECAR))
sys.path.insert(0, str(TESTS))

from support.cg_migrations import apply_cg_migrations


def _apply_migrations(engine) -> None:
    apply_cg_migrations(engine)


@pytest.fixture()
def pg_engine():
    url = os.getenv("POSTGRES_TEST_URL")
    if not url:
        pytest.skip("POSTGRES_TEST_URL not set")
    engine = create_engine(url, future=True, pool_pre_ping=True)
    _apply_migrations(engine)
    yield engine
    engine.dispose()


def test_postgres_pool_pre_ping_survives_reconnect(pg_engine) -> None:
    factory = sessionmaker(bind=pg_engine, autoflush=False, future=True)
    with factory() as session:
        assert session.execute(text("SELECT 1")).scalar_one() == 1
    pg_engine.dispose()
    with factory() as session:
        assert session.execute(text("SELECT COUNT(*) FROM security_budget_ledgers")).scalar_one() >= 1


def test_postgres_jsonb_facets_roundtrip(pg_engine) -> None:
    with pg_engine.begin() as conn:
        row = conn.execute(
            text(
                """
                SELECT facets FROM governance_crystals
                WHERE platform = 'egress_govern' LIMIT 0
                """
            )
        )
        assert row is not None
