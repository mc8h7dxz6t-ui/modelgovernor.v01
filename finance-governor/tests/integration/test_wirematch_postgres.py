"""Postgres integration — WireMatch platform persistence."""
from __future__ import annotations

import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tests.integration.conftest import POSTGRES_URL


def test_wirematch_evaluate_postgres(postgres_engine, monkeypatch):
    import platforms.common.platform_store as ps

    monkeypatch.setenv("DATABASE_URL", POSTGRES_URL)
    ps._engines.clear()
    ps._stores.clear()
    ps._memory_events.clear()

    from platforms.wire_match.main import app

    client = TestClient(app)
    r = client.post(
        "/wire/evaluate",
        json={
            "wire_id": "pg-wire-2",
            "beneficiary_name": "Revlon Lenders Group",
            "beneficiary_account": "US12REV001",
            "reference": "pay",
            "amount": "1000.00",
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["wire_id"] == "pg-wire-2"
    assert body["decision"] in ("APPROVED", "HELD")

    from platforms.common.platform_store import list_platform_events

    events = list_platform_events("wire_match", limit=5)
    assert any(e["operation_id"] == "pg-wire-2" for e in events)
