"""Reusable local JWKS server and RSA JWT minting for live OIDC integration tests."""
from __future__ import annotations

import json
import threading
import time
import uuid
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa


@dataclass
class LiveJwksFixture:
    issuer: str
    audience: str
    jwks_url: str
    kid: str
    private_key_pem: bytes
    _server: Any = None

    def mint_access_token(
        self,
        *,
        subject: str = "integration-user@corp",
        roles: list[str] | None = None,
        expires_in_seconds: int = 300,
    ) -> str:
        now = int(time.time())
        payload: dict[str, Any] = {
            "sub": subject,
            "iss": self.issuer,
            "aud": self.audience,
            "exp": now + expires_in_seconds,
            "iat": now,
        }
        if roles:
            payload["realm_access"] = {"roles": roles}
        return jwt.encode(
            payload,
            self.private_key_pem,
            algorithm="RS256",
            headers={"kid": self.kid},
        )


class _JwksHandler(BaseHTTPRequestHandler):
    jwks_document: str = "{}"

    def do_GET(self) -> None:  # noqa: N802
        if self.path.rstrip("/").endswith("/certs"):
            body = self.jwks_document.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self.send_response(404)
        self.end_headers()

    def log_message(self, _format: str, *_args) -> None:
        return


def start_live_jwks_fixture(*, host: str = "127.0.0.1") -> LiveJwksFixture:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_key_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_key = private_key.public_key()
    public_numbers = public_key.public_numbers()
    kid = f"test-{uuid.uuid4().hex[:8]}"

    def _int_to_base64url(value: int) -> str:
        length = (value.bit_length() + 7) // 8
        return jwt.utils.base64url_encode(value.to_bytes(length, byteorder="big")).decode("ascii")

    jwks = {
        "keys": [
            {
                "kty": "RSA",
                "kid": kid,
                "use": "sig",
                "alg": "RS256",
                "n": _int_to_base64url(public_numbers.n),
                "e": _int_to_base64url(public_numbers.e),
            }
        ]
    }
    _JwksHandler.jwks_document = json.dumps(jwks)

    server = ThreadingHTTPServer((host, 0), _JwksHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    port = server.server_address[1]
    issuer = f"http://{host}:{port}/realms/modelgovernor"
    jwks_url = f"http://{host}:{port}/realms/modelgovernor/protocol/openid-connect/certs"
    fixture = LiveJwksFixture(
        issuer=issuer,
        audience="modelgovernor",
        jwks_url=jwks_url,
        kid=kid,
        private_key_pem=private_key_pem,
        _server=server,
    )
    return fixture


def stop_live_jwks_fixture(fixture: LiveJwksFixture) -> None:
    server = getattr(fixture, "_server", None)
    if server is not None:
        server.shutdown()
