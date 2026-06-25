"""Regression tests for Finance Governor SQL migration parsing."""
from __future__ import annotations

from pathlib import Path

import pytest

from tests.support.fg_migrations import sql_fragments

MIGRATIONS = Path(__file__).resolve().parents[1] / "migrations"


def test_spine_init_creates_tables_before_indexes():
    sql = (MIGRATIONS / "0001_fg_spine_init.sql").read_text()
    frags = sql_fragments(sql)
    table_idx = next(i for i, f in enumerate(frags) if f.startswith("CREATE TABLE governance_crystals"))
    index_idx = next(i for i, f in enumerate(frags) if "idx_fg_crystals_horizon_sweep" in f)
    assert table_idx < index_idx


def test_spine_init_includes_extension_and_seed_data():
    sql = (MIGRATIONS / "0001_fg_spine_init.sql").read_text()
    frags = sql_fragments(sql)
    assert any(f.startswith('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"') for f in frags)
    assert any(f.startswith("INSERT INTO account_ledgers") for f in frags)


@pytest.mark.parametrize("migration", ["0002_fg_hardening.sql", "0003_platform_persistence.sql", "0004_platform_sdk.sql"])
def test_migrations_parse_without_empty_fragments(migration: str):
    sql = (MIGRATIONS / migration).read_text()
    frags = sql_fragments(sql)
    assert frags
    assert all("CREATE" in f or "ALTER" in f or "INSERT" in f for f in frags)
