"""Diagnostic mode and poison-pill avoidance tests."""
from __future__ import annotations

from pathlib import Path
import sys

from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from sidecar.app.config import get_settings
from sidecar.app.db import override_engine
from sidecar.app.diagnostic_mode import clear_diagnostic_mode, diagnostic_snapshot, enter_diagnostic_mode, is_diagnostic_mode
from sidecar.app.main import app
from tests.integration.test_ledger_hardening import _bootstrap_schema, _create_test_engine

TOKEN = "test-token"
HEADERS = {"x-internal-token": TOKEN}


def _configure(tmp_path, monkeypatch):
    engine = _create_test_engine(tmp_path / "diagnostic.sqlite3")
    _bootstrap_schema(engine)
    monkeypatch.setenv("DATABASE_URL", str(engine.url))
    monkeypatch.setenv("REDIS_URL", "redis://example/0")
    monkeypatch.setenv("SIDECAR_INTERNAL_TOKENS", TOKEN)
    get_settings.cache_clear()
    override_engine(engine)


def test_diagnostic_mode_stays_ready_compatible() -> None:
    clear_diagnostic_mode()
    enter_diagnostic_mode(component="test", reason="synthetic violation")
    assert is_diagnostic_mode() is True
    snap = diagnostic_snapshot()
    assert snap["diagnostic_mode"] is True
    assert snap["diagnostic_component"] == "test"
    clear_diagnostic_mode()
    assert is_diagnostic_mode() is False


def test_diagnostic_admin_http_clear_and_status(tmp_path, monkeypatch) -> None:
    _configure(tmp_path, monkeypatch)
    clear_diagnostic_mode()
    enter_diagnostic_mode(component="reconciler", reason="audit mismatch")

    with TestClient(app) as client:
        status = client.get("/internal/diagnostic/status", headers=HEADERS)
        assert status.status_code == 200
        assert status.json()["diagnostic_mode"] is True
        assert status.json()["diagnostic_component"] == "reconciler"

        cleared = client.post("/internal/diagnostic/clear", headers=HEADERS)
        assert cleared.status_code == 200
        assert cleared.json()["diagnostic_mode"] is False
        assert is_diagnostic_mode() is False


def test_reconciler_health_reports_diagnostic_without_failing_liveness() -> None:
    from reconciler.app.health_server import start_health_server
    import urllib.request

    clear_diagnostic_mode()
    enter_diagnostic_mode(component="reconciler", reason="audit failure")
    server = start_health_server(
        port=0,
        is_leader=lambda: False,
        extra_status=lambda: diagnostic_snapshot(),
    )
    port = server.server_address[1]
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/readyz", timeout=2) as resp:
            assert resp.status == 200
            body = resp.read().decode("utf-8")
            assert "diagnostic" in body
    finally:
        server.shutdown()
        clear_diagnostic_mode()
