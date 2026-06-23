"""OIDC RBAC scaffold tests (JWT validation mocked)."""
from __future__ import annotations

from pathlib import Path
import sys
from unittest.mock import patch

from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from sidecar.app.auth_oidc import AuthContext, _extract_roles
from sidecar.app.config import get_settings
from sidecar.app.db import override_engine
from sidecar.app.diagnostic_mode import clear_diagnostic_mode, enter_diagnostic_mode
from sidecar.app.main import app
from tests.integration.test_ledger_hardening import _bootstrap_schema, _create_test_engine

TOKEN = "test-token"
HEADERS = {"x-internal-token": TOKEN}
VIEWER_HEADERS = {"Authorization": "Bearer viewer.jwt"}
ADMIN_HEADERS = {"Authorization": "Bearer admin.jwt"}


def _configure(tmp_path, monkeypatch, *, oidc_enabled: bool = True):
    engine = _create_test_engine(tmp_path / "oidc.sqlite3")
    _bootstrap_schema(engine)
    monkeypatch.setenv("DATABASE_URL", str(engine.url))
    monkeypatch.setenv("REDIS_URL", "redis://example/0")
    monkeypatch.setenv("SIDECAR_INTERNAL_TOKENS", TOKEN)
    monkeypatch.setenv("OIDC_ENABLED", "true" if oidc_enabled else "false")
    monkeypatch.setenv("OIDC_ISSUER_URL", "https://idp.example/realms/modelgovernor")
    monkeypatch.setenv("OIDC_AUDIENCE", "modelgovernor-sidecar")
    monkeypatch.setenv("OIDC_VIEWER_ROLES", "viewer")
    monkeypatch.setenv("OIDC_FINANCIAL_ADMIN_ROLES", "financial-admin")
    get_settings.cache_clear()
    override_engine(engine)


def test_extract_roles_keycloak_and_okta_claims() -> None:
    roles = _extract_roles(
        {
            "realm_access": {"roles": ["financial-admin", "offline_access"]},
            "groups": ["Everyone"],
        }
    )
    assert "financial-admin" in roles
    assert "everyone" in roles


def test_oidc_viewer_can_read_diagnostic_status(tmp_path, monkeypatch) -> None:
    _configure(tmp_path, monkeypatch)
    clear_diagnostic_mode()
    enter_diagnostic_mode(component="test", reason="audit")

    def fake_validate(token: str) -> AuthContext:
        if token == "viewer.jwt":
            return AuthContext(method="oidc", subject="viewer@corp", roles=frozenset({"viewer"}))
        raise AssertionError(f"unexpected token {token}")

    with patch("sidecar.app.auth_oidc._validate_oidc_jwt", side_effect=fake_validate):
        with TestClient(app) as client:
            response = client.get("/internal/diagnostic/status", headers=VIEWER_HEADERS)
            assert response.status_code == 200
            assert response.json()["diagnostic_mode"] is True


def test_oidc_viewer_cannot_clear_diagnostic_mode(tmp_path, monkeypatch) -> None:
    _configure(tmp_path, monkeypatch)
    enter_diagnostic_mode(component="test", reason="audit")

    def fake_validate(token: str) -> AuthContext:
        return AuthContext(method="oidc", subject="viewer@corp", roles=frozenset({"viewer"}))

    with patch("sidecar.app.auth_oidc._validate_oidc_jwt", side_effect=fake_validate):
        with TestClient(app) as client:
            response = client.post("/internal/diagnostic/clear", headers=VIEWER_HEADERS)
            assert response.status_code == 403


def test_oidc_financial_admin_can_clear_diagnostic_mode(tmp_path, monkeypatch) -> None:
    _configure(tmp_path, monkeypatch)
    enter_diagnostic_mode(component="test", reason="audit")

    def fake_validate(token: str) -> AuthContext:
        return AuthContext(method="oidc", subject="admin@corp", roles=frozenset({"financial-admin"}))

    with patch("sidecar.app.auth_oidc._validate_oidc_jwt", side_effect=fake_validate):
        with TestClient(app) as client:
            response = client.post("/internal/diagnostic/clear", headers=ADMIN_HEADERS)
            assert response.status_code == 200
            assert response.json()["diagnostic_mode"] is False


def test_oidc_disabled_uses_internal_token(tmp_path, monkeypatch) -> None:
    _configure(tmp_path, monkeypatch, oidc_enabled=False)
    enter_diagnostic_mode(component="test", reason="audit")

    with TestClient(app) as client:
        response = client.post("/internal/diagnostic/clear", headers=HEADERS)
        assert response.status_code == 200
        assert response.json()["diagnostic_mode"] is False


def test_oidc_enabled_rejects_missing_bearer_without_fallback(tmp_path, monkeypatch) -> None:
    _configure(tmp_path, monkeypatch)
    monkeypatch.setenv("OIDC_ALLOW_INTERNAL_TOKEN_FALLBACK", "false")
    get_settings.cache_clear()

    with TestClient(app) as client:
        assert client.get("/internal/diagnostic/status", headers=HEADERS).status_code == 401
