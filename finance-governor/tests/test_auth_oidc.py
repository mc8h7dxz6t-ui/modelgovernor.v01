"""OIDC RBAC — Finance Governor standalone."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
SIDECAR = ROOT / "spine" / "sidecar"
sys.path.insert(0, str(SIDECAR))

from tests.conftest_spine import spine_db  # noqa: F401

HEADERS = {"x-internal-token": "test-token"}


@pytest.fixture()
def client(spine_db):
    from app.main import app

    return TestClient(app)


def test_internal_token_is_financial_admin_by_default(client):
    from app.auth_oidc import AuthContext

    ctx = AuthContext(method="internal_token", subject="t", roles=frozenset({"viewer"}))
    assert ctx.is_financial_admin() is True


def test_diagnostic_clear_requires_financial_admin(client, monkeypatch):
    from app.config import Settings

    settings = Settings(
        database_url="sqlite://",
        redis_url="redis://localhost",
        fg_internal_tokens="viewer-only",
        oidc_internal_token_is_admin=False,
    )
    monkeypatch.setattr("app.config.get_settings", lambda: settings)
    monkeypatch.setattr("app.auth_oidc.get_settings", lambda: settings)
    r = client.post("/internal/diagnostic/clear", headers={"x-internal-token": "viewer-only"})
    assert r.status_code == 403


def test_diagnostic_clear_records_admin_audit(client):
    r = client.post("/internal/diagnostic/clear", headers=HEADERS)
    assert r.status_code == 200
    audit = client.get("/internal/admin/audit/recent", headers=HEADERS)
    assert any(row["action"] == "diagnostic_clear" for row in audit.json())


def test_anchor_head_requires_auth(client):
    r = client.post("/internal/decisions/anchor-head")
    assert r.status_code == 401
