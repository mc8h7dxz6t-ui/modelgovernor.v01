"""Health server for ig reconciler."""
from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Callable


class _HealthHandler(BaseHTTPRequestHandler):
    is_leader: Callable[[], bool] = lambda: True
    diagnostic_mode: Callable[[], bool] = lambda: False

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return

    def do_GET(self) -> None:  # noqa: N802
        if self.path in {"/healthz", "/readyz"}:
            leader = _HealthHandler.is_leader()
            diagnostic = _HealthHandler.diagnostic_mode()
            if self.path == "/healthz":
                code = 200
                status = "diagnostic" if diagnostic else "ok"
            elif diagnostic:
                code = 200
                status = "diagnostic"
            else:
                code = 200 if leader else 503
                status = "ok" if leader else "standby"
            body = {"status": status, "leader": leader, "diagnostic_mode": diagnostic}
            payload = json.dumps(body).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return
        self.send_response(404)
        self.end_headers()


def start_health_server(
    *,
    port: int,
    is_leader: Callable[[], bool],
    diagnostic_mode: Callable[[], bool] | None = None,
) -> ThreadingHTTPServer:
    _HealthHandler.is_leader = is_leader
    _HealthHandler.diagnostic_mode = diagnostic_mode or (lambda: False)
    server = ThreadingHTTPServer(("0.0.0.0", port), _HealthHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server
