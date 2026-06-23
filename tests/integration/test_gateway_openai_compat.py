"""OpenAI-compatible gateway API tests."""
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


def _setup_gateway_env(tmp_path, monkeypatch, *, user_id: str = "default-user") -> None:
    engine = _create_test_engine(tmp_path / "openai-compat.sqlite3")
    _bootstrap_schema(engine)
    _seed_wallet_and_model(engine, user_id=user_id, balance=Decimal("100"))
    override_engine(engine)
    monkeypatch.setenv("DATABASE_URL", str(engine.url))
    monkeypatch.setenv("REDIS_URL", "redis://example/0")
    monkeypatch.setenv("SIDECAR_INTERNAL_TOKENS", TOKEN)
    monkeypatch.setenv("SIDECAR_URL", "http://sidecar:8081")
    monkeypatch.setenv("SIDECAR_INTERNAL_TOKEN", TOKEN)
    monkeypatch.setenv("MOCK_DISPATCH_COST", "2.000000")
    monkeypatch.setenv("PROVIDER_MODE", "mock")
    monkeypatch.setenv("OPENAI_COMPAT_ENABLED", "true")
    monkeypatch.setenv("OPENAI_COMPAT_API_KEY", TOKEN)
    monkeypatch.setenv("OPENAI_COMPAT_DEFAULT_USER_ID", user_id)
    get_settings.cache_clear()


def test_openai_chat_completions_mock_provider(tmp_path, monkeypatch) -> None:
    _setup_gateway_env(tmp_path, monkeypatch)

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
                "/v1/chat/completions",
                headers={"Authorization": f"Bearer {TOKEN}"},
                json={
                    "model": "gpt-4o-mini",
                    "messages": [{"role": "user", "content": "hello openai compat"}],
                    "user": "default-user",
                },
            )

        assert response.status_code == 200, response.text
        body = response.json()
        assert body["object"] == "chat.completion"
        assert body["model"] == "gpt-4o-mini"
        assert body["choices"][0]["message"]["role"] == "assistant"
        assert body["choices"][0]["message"]["content"].startswith("mock:")
        assert body["usage"]["prompt_tokens"] > 0
        assert body["usage"]["completion_tokens"] > 0

        wallet = sidecar_client.get("/internal/wallet/default-user", headers={"x-internal-token": TOKEN})
        assert wallet.status_code == 200
        assert Decimal(wallet.json()["balance"]) < Decimal("100.000000")


def test_openai_list_models(tmp_path, monkeypatch) -> None:
    _setup_gateway_env(tmp_path, monkeypatch)

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
            response = gateway_client.get(
                "/v1/models",
                headers={"Authorization": f"Bearer {TOKEN}"},
            )

    assert response.status_code == 200
    body = response.json()
    assert body["object"] == "list"
    assert any(entry["id"] == "gpt-4o-mini" for entry in body["data"])


def test_openai_chat_rejects_streaming(tmp_path, monkeypatch) -> None:
    _setup_gateway_env(tmp_path, monkeypatch)

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
                "/v1/chat/completions",
                headers={"Authorization": f"Bearer {TOKEN}"},
                json={
                    "model": "gpt-4o-mini",
                    "messages": [{"role": "user", "content": "stream?"}],
                    "stream": True,
                },
            )

    assert response.status_code == 400
