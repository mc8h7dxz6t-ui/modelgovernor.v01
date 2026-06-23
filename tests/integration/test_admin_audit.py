"""Privileged admin audit log tests."""
from __future__ import annotations

from pathlib import Path
import sys
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import text

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from sidecar.app.auth_oidc import AuthContext
from sidecar.app.config import get_settings
from sidecar.app.db import override_engine
from sidecar.app.diagnostic_mode import clear_diagnostic_mode, enter_diagnostic_mode
from sidecar.app.main import app
from tests.integration.test_ledger_hardening import _bootstrap_schema, _create_test_engine

TOKEN = "test-token"
HEADERS = {"x-internal-token": TOKEN}
ADMIN_HEADERS = {"Authorization": "Bearer admin.jwt"}


def _configure(tmp_path, monkeypatch):
    engine = _create_test_engine(tmp_path / "admin-audit.sqlite3")
    _bootstrap_schema(engine)
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE admin_audit_log (
                    audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    actor_subject TEXT NOT NULL,
                    actor_method TEXT NOT NULL,
                    actor_roles TEXT,
                    action TEXT NOT NULL,
                    resource TEXT NOT NULL,
                    details TEXT NOT NULL DEFAULT '{}',
                    prev_hash CHAR(64),
                    row_hash CHAR(64),
                    recorded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        )
    monkeypatch.setenv("DATABASE_URL", str(engine.url))
    monkeypatch.setenv("REDIS_URL", "redis://example/0")
    monkeypatch.setenv("SIDECAR_INTERNAL_TOKENS", TOKEN)
    monkeypatch.setenv("OIDC_ENABLED", "true")
    monkeypatch.setenv("OIDC_ISSUER_URL", "https://idp.example/realms/modelgovernor")
    get_settings.cache_clear()
    override_engine(engine)


def test_clear_diagnostic_writes_admin_audit_entry(tmp_path, monkeypatch) -> None:
    _configure(tmp_path, monkeypatch)
    enter_diagnostic_mode(component="test", reason="audit")

    def fake_validate(token: str) -> AuthContext:
        return AuthContext(method="oidc", subject="admin@corp", roles=frozenset({"financial-admin"}))

    with patch("sidecar.app.auth_oidc._validate_oidc_jwt", side_effect=fake_validate):
        with TestClient(app) as client:
            response = client.post("/internal/diagnostic/clear", headers=ADMIN_HEADERS)
            assert response.status_code == 200

            audit = client.get("/internal/admin/audit/recent", headers=HEADERS)
            assert audit.status_code == 200
            body = audit.json()
            assert body["total"] >= 1
            assert body["entries"][0]["action"] == "diagnostic.clear"
            assert body["entries"][0]["actor_subject"] == "admin@corp"

    clear_diagnostic_mode()
