"""Postgres-backed platform persistence integration."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def test_subledger_postgres_roundtrip(postgres_engine, monkeypatch):
    import platforms.common.platform_store as ps
    from platforms.common.platform_store import get_subledger_store

    url = str(postgres_engine.url)
    monkeypatch.setenv("DATABASE_URL", url)
    ps._engines.clear()
    ps._stores.clear()

    store = get_subledger_store()
    store.reset()
    assert store.ingest(
        txn_hash="hash-pg-1",
        record={
            "entity_id": "E1",
            "counterparty_id": "E2",
            "amount": "500.00",
            "currency": "USD",
            "value_date": "2026-06-01",
            "reference": "",
        },
    )
    assert store.count_pending() == 1
