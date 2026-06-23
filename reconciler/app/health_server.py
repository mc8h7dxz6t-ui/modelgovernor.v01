"""Minimal HTTP health server for Kubernetes probes."""
from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Callable


class _HealthHandler(BaseHTTPRequestHandler):
    is_leader: Callable[[], bool] = lambda: True

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return

    def do_GET(self) -> None:  # noqa: N802
        if self.path in {"/healthz", "/readyz"}:
            body = {"status": "ok" if self.is_leader() or self.path == "/healthz" else "standby"}
            code = 200 if self.path == "/healthz" or self.is_leader() else 503
            payload = json.dumps(body).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return
        self.send_response(404)
        self.end_headers()


def start_health_server(*, port: int, is_leader: Callable[[], bool]) -> ThreadingHTTPServer:
    _HealthHandler.is_leader = is_leader
    server = ThreadingHTTPServer(("0.0.0.0", port), _HealthHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True, name="reconciler-health")
    thread.start()
    return server
