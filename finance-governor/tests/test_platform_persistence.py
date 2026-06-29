"""Durable platform store — SQLite-backed persistence tests."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

SCHEMA = (Path(__file__).parent / "schema_sqlite.sql").read_text()


@pytest.fixture()
def sqlite_store(monkeypatch):
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    with engine.begin() as conn:
        from tests.support.fg_migrations import sql_fragments

        for fragment in sql_fragments(SCHEMA):
            conn.execute(text(fragment))
    monkeypatch.setenv("DATABASE_URL", "sqlite+pysqlite:///:memory:")
    import platforms.common.platform_store as ps

    ps._engines.clear()
    ps._stores.clear()
    ps._engines["sqlite+pysqlite:///:memory:"] = engine
    yield ps
    ps._engines.clear()
    ps._stores.clear()
    monkeypatch.delenv("DATABASE_URL", raising=False)


def test_subledger_sqlite_ingest_and_match(sqlite_store):
    from platforms.common.platform_store import get_subledger_store

    store = get_subledger_store()
    assert store.ingest(
        txn_hash="abc",
        record={
            "entity_id": "UK",
            "counterparty_id": "US",
            "amount": "100.00",
            "currency": "USD",
            "value_date": "2026-06-01",
            "reference": "",
        },
    )
    assert store.count_pending() == 1
    assert not store.ingest(
        txn_hash="abc",
        record={
            "entity_id": "UK",
            "counterparty_id": "US",
            "amount": "100.00",
            "currency": "USD",
            "value_date": "2026-06-01",
            "reference": "",
        },
    )


def test_asset_sqlite_depreciation_idempotent(sqlite_store):
    from platforms.common.platform_store import get_asset_store

    store = get_asset_store()
    store.register_asset(
        {
            "asset_id": "a1",
            "description": "rack",
            "acquisition_cost": "1200.00",
            "book_value": "1200.00",
            "accumulated_depreciation": "0",
            "method": "straight_line",
            "jurisdiction": "US",
            "useful_life_months": 60,
        }
    )
    row1 = store.apply_charge(asset_id="a1", period="2026-06", charge="20.00", reg_table_version="v1", crystal_id=None)
    row2 = store.apply_charge(asset_id="a1", period="2026-06", charge="20.00", reg_table_version="v1", crystal_id=None)
    assert row1 is not None
    assert row2 is None


def test_credit_sqlite_evaluation_record(sqlite_store):
    from platforms.common.platform_store import get_credit_store

    store = get_credit_store()
    assert store.record_evaluation(
        {
            "application_id": "app-1",
            "decision": "APPROVE",
            "exposure_amount": "1000.00",
            "model_version_id": "credit-model-v3",
            "desk_id": "desk-default",
            "score": 0.8,
            "explanation_id": "exp-1",
            "crystal_id": None,
        }
    )
    row = store.get_evaluation("app-1")
    assert row is not None
    assert row["decision"] == "APPROVE"
