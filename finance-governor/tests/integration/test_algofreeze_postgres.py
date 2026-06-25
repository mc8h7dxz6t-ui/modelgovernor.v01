"""Postgres integration — AlgoFreeze platform."""
from __future__ import annotations

import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tests.integration.conftest import POSTGRES_URL


def test_algofreeze_order_postgres(postgres_engine, monkeypatch):
    import platforms.common.platform_store as ps

    monkeypatch.setenv("DATABASE_URL", POSTGRES_URL)
    ps._engines.clear()
    ps._stores.clear()

    from platforms.algofreeze.main import app

    client = TestClient(app)
    r = client.post(
        "/orders",
        json={"order_id": "pg-algo-1", "runtime_sha": "approved-sha-v1"},
    )
    assert r.status_code in (200, 403)
