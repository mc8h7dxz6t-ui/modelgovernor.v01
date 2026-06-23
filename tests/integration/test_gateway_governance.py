"""Gateway reserve/settle integration tests."""
from __future__ import annotations

from decimal import Decimal
from pathlib import Path
import sys

from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from sidecar.app.config import get_settings
from sidecar.app.db import override_engine
from sidecar.app.main import app as sidecar_app
from tests.integration.test_ledger_hardening import _bootstrap_schema, _create_test_engine, _seed_wallet_and_model

TOKEN = "test-token"


class _SidecarForwardingClient:
    def __init__(self, sidecar: TestClient) -> None:
        self._sidecar = sidecar

    def __enter__(self):
        return self

    def __exit__(self, *_args) -> None:
        return None

    def post(self, url: str, **kwargs):
        path = url.split("://", 1)[-1]
        path = "/" + path.split("/", 1)[-1]
        return self._sidecar.post(path, headers=kwargs.get("headers"), json=kwargs.get("json"))

    def get(self, url: str, **kwargs):
        path = url.split("://", 1)[-1]
        path = "/" + path.split("/", 1)[-1]
        return self._sidecar.get(path, headers=kwargs.get("headers"))


def test_gateway_governed_dispatch_reserve_settle(tmp_path, monkeypatch) -> None:
    engine = _create_test_engine(tmp_path / "gateway.sqlite3")
    _bootstrap_schema(engine)
    _seed_wallet_and_model(engine, user_id="gw-user", balance=Decimal("100"))
    override_engine(engine)
    monkeypatch.setenv("DATABASE_URL", str(engine.url))
    monkeypatch.setenv("REDIS_URL", "redis://example/0")
    monkeypatch.setenv("SIDECAR_INTERNAL_TOKENS", TOKEN)
    monkeypatch.setenv("SIDECAR_URL", "http://sidecar:8081")
    monkeypatch.setenv("SIDECAR_INTERNAL_TOKEN", TOKEN)
    monkeypatch.setenv("MOCK_DISPATCH_COST", "1.000000")
    get_settings.cache_clear()

    from gateway.app import main as gateway_main
    from gateway.app.config import get_settings as gateway_get_settings

    gateway_get_settings.cache_clear()

    with TestClient(sidecar_app) as sidecar_client:
        monkeypatch.setattr(
            gateway_main.httpx,
            "Client",
            lambda **kwargs: _SidecarForwardingClient(sidecar_client),
        )
        with TestClient(gateway_main.app) as gateway_client:
            response = gateway_client.post(
                "/governed/dispatch",
                headers={"x-internal-token": TOKEN},
                json={
                    "user_id": "gw-user",
                    "trace_id": "gw-trace",
                    "model": "gpt-4o-mini",
                    "estimated_cost": "5.000000",
                    "idempotency_key": "gw-op-1",
                },
            )

        assert response.status_code == 200, response.text
        body = response.json()
        assert body["reserve_status"] == "RESERVED"
        assert body["settle_status"] == "SETTLED"
        assert Decimal(body["actual_cost"]) == Decimal("1.000000")
        assert body["authenticated_subject"] == "internal-token"

        wallet = sidecar_client.get("/internal/wallet/gw-user", headers={"x-internal-token": TOKEN})
        assert wallet.status_code == 200
        assert Decimal(wallet.json()["balance"]) == Decimal("99.000000")
