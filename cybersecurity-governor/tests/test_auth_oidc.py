"""OIDC RBAC tests for Cybersecurity Governor sidecar."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
SIDECAR = ROOT / "spine" / "sidecar"
sys.path.insert(0, str(SIDECAR))

from app.auth_oidc import AuthContext, _extract_roles
from app.config import Settings, get_settings, override_settings
from app.db import override_engine
from app.diagnostic_mode import clear_diagnostic_mode, enter_diagnostic_mode
from app.guardrails import reset_guardrails
from app.main import app

TOKEN = "test-token"
HEADERS = {"x-internal-token": TOKEN}
VIEWER_HEADERS = {"Authorization": "Bearer viewer.jwt"}
ADMIN_HEADERS = {"Authorization": "Bearer admin.jwt"}


def _configure(spine_db, monkeypatch, *, oidc_enabled: bool = True):
    override_settings(
        Settings(
            database_url=str(spine_db.url),
            redis_url="redis://example/0",
            cg_internal_tokens=TOKEN,
            oidc_enabled=oidc_enabled,
            oidc_issuer_url="https://idp.example/realms/cybersecuritygovernor",
            oidc_audience="cybersecuritygovernor-sidecar",
            oidc_viewer_roles="viewer",
            oidc_claims_admin_roles="security-admin",
            guardrails_enabled=False,
        )
    )
    monkeypatch.setattr("app.config.get_settings", get_settings)
    override_engine(spine_db)
    reset_guardrails()


def test_extract_roles_keycloak_and_okta_claims() -> None:
    roles = _extract_roles(
        {
            "realm_access": {"roles": ["security-admin", "offline_access"]},
            "groups": ["Everyone"],
        }
    )
    assert "security-admin" in roles
    assert "everyone" in roles


def test_oidc_viewer_can_read_diagnostic_status(spine_db, monkeypatch) -> None:
    _configure(spine_db, monkeypatch)
    clear_diagnostic_mode()
    enter_diagnostic_mode(component="test", reason="audit")

    def fake_validate(token: str) -> AuthContext:
        if token == "viewer.jwt":
            return AuthContext(method="oidc", subject="viewer@corp", roles=frozenset({"viewer"}))
        raise AssertionError(f"unexpected token {token}")

    with patch("app.auth_oidc._validate_oidc_jwt", side_effect=fake_validate):
        with TestClient(app) as client:
            response = client.get("/internal/diagnostic/status", headers=VIEWER_HEADERS)
            assert response.status_code == 200
            assert response.json()["diagnostic_mode"] is True


def test_oidc_viewer_cannot_clear_diagnostic_mode(spine_db, monkeypatch) -> None:
    _configure(spine_db, monkeypatch)
    enter_diagnostic_mode(component="test", reason="audit")

    def fake_validate(token: str) -> AuthContext:
        return AuthContext(method="oidc", subject="viewer@corp", roles=frozenset({"viewer"}))

    with patch("app.auth_oidc._validate_oidc_jwt", side_effect=fake_validate):
        with TestClient(app) as client:
            response = client.post("/internal/diagnostic/clear", headers=VIEWER_HEADERS)
            assert response.status_code == 403


def test_oidc_claims_admin_can_clear_diagnostic_mode(spine_db, monkeypatch) -> None:
    _configure(spine_db, monkeypatch)
    enter_diagnostic_mode(component="test", reason="audit")

    def fake_validate(token: str) -> AuthContext:
        return AuthContext(method="oidc", subject="admin@corp", roles=frozenset({"security-admin"}))

    with patch("app.auth_oidc._validate_oidc_jwt", side_effect=fake_validate):
        with TestClient(app) as client:
            response = client.post("/internal/diagnostic/clear", headers=ADMIN_HEADERS)
            assert response.status_code == 200
            assert response.json()["cleared"] is True
