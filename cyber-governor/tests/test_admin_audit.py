"""Privileged admin audit log tests."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
SIDECAR = ROOT / "spine" / "sidecar"
sys.path.insert(0, str(SIDECAR))

from app.auth_oidc import AuthContext
from app.config import Settings, get_settings
from app.db import override_engine
from app.diagnostic_mode import clear_diagnostic_mode, enter_diagnostic_mode
from app.main import app
from tests.helpers import create_sqlite_engine

TOKEN = "test-token"
HEADERS = {"x-internal-token": TOKEN}
ADMIN_HEADERS = {"Authorization": "Bearer admin.jwt"}


def _configure(tmp_path, monkeypatch):
    engine = create_sqlite_engine(tmp_path / "admin-audit.sqlite3")
    test_settings = Settings(
        database_url=str(engine.url),
        redis_url="redis://example/0",
        cg_internal_tokens=TOKEN,
        oidc_enabled=True,
        oidc_issuer_url="https://idp.example/realms/cybersecuritygovernor",
        oidc_audience="cybersecuritygovernor-sidecar",
        oidc_security_admin_roles="security-admin",
    )
    get_settings.cache_clear()
    monkeypatch.setattr("app.config.get_settings", lambda: test_settings)
    monkeypatch.setattr("app.auth_oidc.get_settings", lambda: test_settings)
    override_engine(engine)


def test_clear_diagnostic_writes_admin_audit_entry(tmp_path, monkeypatch) -> None:
    _configure(tmp_path, monkeypatch)
    enter_diagnostic_mode(component="test", reason="audit")

    def fake_validate(token: str) -> AuthContext:
        return AuthContext(method="oidc", subject="admin@corp", roles=frozenset({"security-admin"}))

    with patch("app.auth_oidc._validate_oidc_jwt", side_effect=fake_validate):
        with TestClient(app) as client:
            response = client.post("/internal/diagnostic/clear", headers=ADMIN_HEADERS)
            assert response.status_code == 200

            audit = client.get("/internal/admin/audit/recent", headers=HEADERS)
            assert audit.status_code == 200
            body = audit.json()
            assert body["total"] >= 1
            assert body["entries"][0]["action"] == "diagnostic_clear"
            assert body["entries"][0]["actor_subject"] == "admin@corp"

    clear_diagnostic_mode()
