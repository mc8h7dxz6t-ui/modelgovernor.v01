"""Minimal HTTP health + metrics server for Kubernetes probes."""
from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Callable


class _HealthHandler(BaseHTTPRequestHandler):
    is_leader: Callable[[], bool] = lambda: True
    extra_status: Callable[[], dict] = lambda: {}

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/metrics/prometheus":
            payload = _prometheus_payload().encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; version=0.0.4")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return

        if self.path in {"/healthz", "/readyz"}:
            extra = _HealthHandler.extra_status()
            diagnostic = bool(extra.get("diagnostic_mode"))
            leader = _HealthHandler.is_leader()
            if self.path == "/healthz":
                status = "diagnostic" if diagnostic else "ok"
                code = 200
            elif diagnostic:
                status = "diagnostic"
                code = 200
            elif leader:
                status = "ok"
                code = 200
            else:
                status = "standby"
                code = 503

            body = {"status": status, "leader": leader, **extra}
            payload = json.dumps(body).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return
        self.send_response(404)
        self.end_headers()


def _prometheus_payload() -> str:
    try:
        from prometheus_client import generate_latest

        return generate_latest().decode("utf-8")
    except ImportError:
        pass
    try:
        from sidecar.app.metrics import get_counters

        lines = [
            "# HELP modelgovernor_invariant_events_total Process-level invariant counters.",
            "# TYPE modelgovernor_invariant_events_total counter",
        ]
        for event_name, value in sorted(get_counters().snapshot().items()):
            lines.append(f'modelgovernor_invariant_events_total{{event="{event_name}"}} {value}')
        lines.extend(
            [
                "# HELP modelgovernor_reconciler_leader Leader status (1=leader).",
                "# TYPE modelgovernor_reconciler_leader gauge",
                f"modelgovernor_reconciler_leader {_HealthHandler.is_leader() and 1 or 0}",
            ]
        )
        return "\n".join(lines) + "\n"
    except ImportError:
        return "# reconciler metrics unavailable\n"


def start_health_server(
    *,
    port: int,
    is_leader: Callable[[], bool],
    is_healthy: Callable[[], bool] | None = None,
    extra_status: Callable[[], dict] | None = None,
) -> ThreadingHTTPServer:
    _HealthHandler.is_leader = is_leader
    _HealthHandler.extra_status = extra_status or (lambda: {})
    server = ThreadingHTTPServer(("0.0.0.0", port), _HealthHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True, name="reconciler-health")
    thread.start()
    return server
