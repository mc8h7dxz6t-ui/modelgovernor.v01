#!/usr/bin/env python3
"""Minimal FedNow sandbox HTTP server for staging rail smoke."""
from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, HTTPServer


class FedNowHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path in ("/healthz", "/v1/payments"):
            payload = b'{"status":"ok","sandbox":true}'
            self.send_response(200)
            self.send_header("content-type", "application/json")
            self.send_header("content-length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return
        self.send_error(404)

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length).decode() or "{}")
        tx_id = f"fednow-sbx-{body.get('idempotencyKey', 'unknown')[:12]}"
        response = {"transactionId": tx_id, "status": "COMPLETED", "sandbox": True}
        payload = json.dumps(response).encode()
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return


def main() -> None:
    port = int(__import__("os").environ.get("FEDNOW_SANDBOX_PORT", "8190"))
    server = HTTPServer(("0.0.0.0", port), FedNowHandler)
    print(f"FedNow sandbox listening on :{port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
