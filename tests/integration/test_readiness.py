from __future__ import annotations

from pathlib import Path
import sys

from fastapi.testclient import TestClient
from sqlalchemy import text

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from sidecar.app.config import get_settings
from sidecar.app.db import override_engine
from sidecar.app.main import app
from sidecar.app.metrics import get_counters
from tests.integration.test_ledger_hardening import _bootstrap_schema, _create_test_engine, _seed_wallet_and_model

TOKEN = "test-token"
HEADERS = {"x-internal-token": TOKEN}


def _configure(tmp_path: Path, monkeypatch) -> None:
    engine = _create_test_engine(tmp_path / "readiness.sqlite3")
    _bootstrap_schema(engine)
    _seed_wallet_and_model(engine, user_id="user-1")
    override_engine(engine)
    monkeypatch.setenv("DATABASE_URL", str(engine.url))
    monkeypatch.setenv("REDIS_URL", "redis://example/0")
    monkeypatch.setenv("SIDECAR_INTERNAL_TOKENS", TOKEN)
    get_settings.cache_clear()


def test_readyz_probes_database(tmp_path: Path, monkeypatch) -> None:
    _configure(tmp_path, monkeypatch)
    with TestClient(app) as client:
        assert client.get("/readyz").json() == {"status": "ready"}


def test_readyz_fails_when_database_unavailable(monkeypatch) -> None:
    from contextlib import contextmanager

    @contextmanager
    def broken_db_session():
        raise ConnectionError("database unavailable")
        yield  # pragma: no cover

    monkeypatch.setattr("sidecar.app.main.get_db_session", broken_db_session)

    with TestClient(app) as client:
        response = client.get("/readyz")
        assert response.status_code == 503


def test_metrics_json_exposes_invariant_counters(tmp_path: Path, monkeypatch) -> None:
    _configure(tmp_path, monkeypatch)
    get_counters().reset()
    get_counters().increment("reserve_success_total", 3)

    with TestClient(app) as client:
        payload = client.get("/metrics.json").json()
        assert payload["reserve_success_total"] == 3


def test_metrics_text_includes_invariant_counters(tmp_path: Path, monkeypatch) -> None:
    _configure(tmp_path, monkeypatch)
    get_counters().reset()
    get_counters().increment("drift_enforced_total")

    with TestClient(app) as client:
        body = client.get("/metrics", headers=HEADERS).text
        assert "modelgovernor_invariant_events_total" in body
        assert 'event="drift_enforced_total"' in body
