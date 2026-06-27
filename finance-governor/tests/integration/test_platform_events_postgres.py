"""Postgres platform event audit for AlgoFreeze and WireMatch."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


from tests.integration.conftest import POSTGRES_URL


def test_wirematch_events_persisted_postgres(postgres_engine, monkeypatch):
    import platforms.common.platform_store as ps
    from platforms.common.platform_store import list_platform_events

    monkeypatch.setenv("DATABASE_URL", POSTGRES_URL)
    ps._engines.clear()
    ps._stores.clear()
    ps._memory_events.clear()

    from platforms.wire_match.main import app

    client = TestClient(app)
    client.post(
        "/wire/evaluate",
        json={
            "wire_id": "pg-wire-1",
            "beneficiary_name": "Revlon Lenders Group",
            "beneficiary_account": "US12REV001",
            "reference": "pay",
            "amount": "7800000.00",
        },
    )
    events = list_platform_events("wire_match", limit=5)
    assert len(events) >= 1
    assert events[0]["operation_id"] == "pg-wire-1"
