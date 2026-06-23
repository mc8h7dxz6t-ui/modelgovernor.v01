"""Live JWKS OIDC validation — no mocks, real RSA + PyJWKClient."""
from __future__ import annotations

from pathlib import Path
import sys

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from sidecar.app.auth_oidc import _validate_oidc_jwt, clear_jwks_client_cache
from sidecar.app.config import get_settings
from sidecar.app.db import override_engine
from sidecar.app.main import app
from tests.integration.test_ledger_hardening import _bootstrap_schema, _create_test_engine
from tests.support.oidc_jwks_fixture import start_live_jwks_fixture, stop_live_jwks_fixture

TOKEN = "test-token"


def _configure_oidc(monkeypatch, fixture) -> None:
    monkeypatch.setenv("OIDC_ENABLED", "true")
    monkeypatch.setenv("OIDC_ISSUER_URL", fixture.issuer)
    monkeypatch.setenv("OIDC_AUDIENCE", fixture.audience)
    monkeypatch.setenv("OIDC_JWKS_URL", fixture.jwks_url)
    monkeypatch.setenv("OIDC_VIEWER_ROLES", "viewer")
    monkeypatch.setenv("OIDC_FINANCIAL_ADMIN_ROLES", "financial-admin")
    get_settings.cache_clear()
    clear_jwks_client_cache()


def test_sidecar_validates_live_jwks_signed_jwt(tmp_path, monkeypatch) -> None:
    engine = _create_test_engine(tmp_path / "jwks-live.sqlite3")
    _bootstrap_schema(engine)
    monkeypatch.setenv("DATABASE_URL", str(engine.url))
    monkeypatch.setenv("REDIS_URL", "redis://example/0")
    monkeypatch.setenv("SIDECAR_INTERNAL_TOKENS", TOKEN)
    override_engine(engine)

    fixture = start_live_jwks_fixture()
    try:
        _configure_oidc(monkeypatch, fixture)
        token = fixture.mint_access_token(roles=["viewer"])
        ctx = _validate_oidc_jwt(token)
        assert ctx.subject == "integration-user@corp"
        assert ctx.is_viewer() is True

        with TestClient(app) as client:
            response = client.get(
                "/internal/diagnostic/status",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert response.status_code == 200
    finally:
        stop_live_jwks_fixture(fixture)


def test_sidecar_rejects_tampered_live_jwt(tmp_path, monkeypatch) -> None:
    engine = _create_test_engine(tmp_path / "jwks-bad.sqlite3")
    _bootstrap_schema(engine)
    monkeypatch.setenv("DATABASE_URL", str(engine.url))
    monkeypatch.setenv("REDIS_URL", "redis://example/0")
    monkeypatch.setenv("SIDECAR_INTERNAL_TOKENS", TOKEN)
    override_engine(engine)

    fixture = start_live_jwks_fixture()
    try:
        _configure_oidc(monkeypatch, fixture)
        token = fixture.mint_access_token(roles=["viewer"]) + "tampered"
        with pytest.raises(HTTPException):
            _validate_oidc_jwt(token)
    finally:
        stop_live_jwks_fixture(fixture)


def test_gateway_validates_live_jwks_for_dispatch(tmp_path, monkeypatch) -> None:
    from gateway.app.auth_oidc import _validate_oidc_jwt, clear_jwks_client_cache
    from gateway.app.config import get_settings as gateway_settings

    fixture = start_live_jwks_fixture()
    try:
        monkeypatch.setenv("OIDC_ENABLED", "true")
        monkeypatch.setenv("OIDC_ISSUER_URL", fixture.issuer)
        monkeypatch.setenv("OIDC_AUDIENCE", fixture.audience)
        monkeypatch.setenv("OIDC_JWKS_URL", fixture.jwks_url)
        monkeypatch.setenv("OIDC_DISPATCH_ROLES", "dispatch")
        monkeypatch.setenv("SIDECAR_INTERNAL_TOKEN", "dev-token")
        gateway_settings.cache_clear()
        clear_jwks_client_cache()

        token = fixture.mint_access_token(roles=["dispatch"])
        ctx = _validate_oidc_jwt(token)
        assert ctx.can_dispatch() is True
    finally:
        stop_live_jwks_fixture(fixture)
