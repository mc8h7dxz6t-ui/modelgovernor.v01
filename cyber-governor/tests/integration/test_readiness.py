"""Sidecar readiness and observability endpoints."""
from __future__ import annotations

import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
SIDECAR = ROOT / "spine" / "sidecar"
sys.path.insert(0, str(SIDECAR))

from tests.conftest_spine import spine_db  # noqa: F401


def test_healthz_readyz_metrics(spine_db, monkeypatch):
    from app.config import Settings
    from app.main import app

    monkeypatch.setattr(
        "app.config.get_settings",
        lambda: Settings(
            database_url="sqlite+pysqlite:///:memory:",
            redis_url="redis://localhost:6390/0",
            cg_internal_tokens="test-token",
        ),
    )
    client = TestClient(app)
    assert client.get("/healthz").json()["status"] == "ok"
    assert client.get("/readyz").json()["status"] == "ready"
    metrics = client.get("/metrics.json").json()
    assert "crystallize_success_total" in metrics
