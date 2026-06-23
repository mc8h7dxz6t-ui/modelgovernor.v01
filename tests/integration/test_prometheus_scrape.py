"""Prometheus scrape surface tests."""
from __future__ import annotations

from pathlib import Path
import sys

from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from sidecar.app.config import get_settings
from sidecar.app.db import override_engine
from sidecar.app.main import app
from sidecar.app.metrics import get_counters
from tests.integration.test_ledger_hardening import _bootstrap_schema, _create_test_engine, _seed_wallet_and_model

TOKEN = "test-token"


def _configure(tmp_path: Path, monkeypatch) -> None:
    engine = _create_test_engine(tmp_path / "prom.sqlite3")
    _bootstrap_schema(engine)
    _seed_wallet_and_model(engine, user_id="user-1")
    override_engine(engine)
    monkeypatch.setenv("DATABASE_URL", str(engine.url))
    monkeypatch.setenv("REDIS_URL", "redis://example/0")
    monkeypatch.setenv("SIDECAR_INTERNAL_TOKENS", TOKEN)
    get_settings.cache_clear()
    get_guardrails_cache_clear()


def get_guardrails_cache_clear() -> None:
    from sidecar.app.guardrails import get_guardrails

    get_guardrails.cache_clear()


def test_metrics_prometheus_unauthenticated(tmp_path, monkeypatch) -> None:
    _configure(tmp_path, monkeypatch)
    get_counters().reset()
    get_counters().increment("reserve_success_total", 2)

    with TestClient(app) as client:
        response = client.get("/metrics/prometheus")
        assert response.status_code == 200
        assert "modelgovernor_invariant_events_total" in response.text
        assert "reserve_success_total" in response.text


def test_metrics_full_still_requires_auth(tmp_path, monkeypatch) -> None:
    _configure(tmp_path, monkeypatch)
    with TestClient(app) as client:
        assert client.get("/metrics").status_code == 401
        assert client.get("/metrics", headers={"x-internal-token": TOKEN}).status_code == 200
