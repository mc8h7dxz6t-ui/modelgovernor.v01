"""Gateway auth on governed commit."""
from __future__ import annotations

import importlib
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
GATEWAY = ROOT / "spine" / "gateway"
SIDECAR = ROOT / "spine" / "sidecar"


def _purge_app_modules() -> None:
    for name in list(sys.modules):
        if name == "app" or name.startswith("app."):
            del sys.modules[name]


def _load_gateway_app(monkeypatch):
    _purge_app_modules()
    if str(GATEWAY) not in sys.path:
        sys.path.insert(0, str(GATEWAY))
    import app.config as gateway_config

    monkeypatch.setattr(
        gateway_config,
        "get_settings",
        lambda: gateway_config.Settings(
            fg_internal_token="gw-test-token",
            fg_sidecar_url="http://localhost:8091",
        ),
    )
    return importlib.import_module("app.main")


@pytest.fixture()
def gateway_client(monkeypatch):
    gateway_main = _load_gateway_app(monkeypatch)
    client = TestClient(gateway_main.app)
    yield client, gateway_main
    _purge_app_modules()
    if str(SIDECAR) not in sys.path:
        sys.path.insert(0, str(SIDECAR))


def test_governed_commit_requires_auth(gateway_client):
    client, _ = gateway_client
    r = client.post(
        "/governed/commit",
        json={"platform": "wire_match", "operation_id": "gw-1", "facets": {"amount": "1.00"}},
    )
    assert r.status_code == 401


def test_governed_commit_with_auth(gateway_client):
    client, gateway_main = gateway_client
    with patch.object(
        gateway_main,
        "execute_governed_commit",
        return_value={"crystal_id": "crys_test", "status": "COMMITTED"},
    ):
        r = client.post(
            "/governed/commit",
            headers={"x-internal-token": "gw-test-token"},
            json={"platform": "wire_match", "operation_id": "gw-2", "facets": {"amount": "1.00"}},
        )
    assert r.status_code == 200
    assert r.json()["status"] == "COMMITTED"
