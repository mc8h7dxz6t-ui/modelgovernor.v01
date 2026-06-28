#!/usr/bin/env python3
"""Minimal Guidewire / Snapsheet PAS writeback sandbox for FNOL integration smoke."""
from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any

_LOCK = threading.Lock()
_WRITEBACKS: list[dict[str, Any]] = []


class PasWritebackHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path != "/stats":
            self.send_error(404)
            return
        with _LOCK:
            payload = json.dumps({"writebacks": list(_WRITEBACKS)}, indent=2).encode()
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length).decode() or "{}")
        vendor = "guidewire" if self.path.startswith("/guidewire") else "snapsheet"
        record = {"vendor": vendor, "path": self.path, "body": body}
        with _LOCK:
            _WRITEBACKS.append(record)
        response = {"id": f"{vendor}-sync-{len(_WRITEBACKS)}", "status": "ACCEPTED", "sandbox": True}
        payload = json.dumps(response).encode()
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return


def main() -> None:
    port = int(__import__("os").environ.get("PAS_WRITEBACK_SANDBOX_PORT", "8191"))
    server = HTTPServer(("0.0.0.0", port), PasWritebackHandler)
    print(f"PAS writeback sandbox listening on :{port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
