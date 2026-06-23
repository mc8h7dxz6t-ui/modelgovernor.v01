"""Diagnostic mode and poison-pill avoidance tests."""
from __future__ import annotations

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from sidecar.app.diagnostic_mode import clear_diagnostic_mode, diagnostic_snapshot, enter_diagnostic_mode, is_diagnostic_mode


def test_diagnostic_mode_stays_ready_compatible() -> None:
    clear_diagnostic_mode()
    enter_diagnostic_mode(component="test", reason="synthetic violation")
    assert is_diagnostic_mode() is True
    snap = diagnostic_snapshot()
    assert snap["diagnostic_mode"] is True
    assert snap["diagnostic_component"] == "test"
    clear_diagnostic_mode()
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
