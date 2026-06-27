"""Reserve route shadow/enforce intercept wiring tests."""
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
from sidecar.app.main import app
from tests.integration.test_ledger_hardening import _bootstrap_schema, _create_test_engine, _seed_wallet_and_model

TOKEN = "test-token"
HEADERS = {"x-internal-token": TOKEN}


def _configure(tmp_path: Path, monkeypatch, **env_overrides: str) -> TestClient:
    engine = _create_test_engine(tmp_path / "enforce.sqlite3")
    _bootstrap_schema(engine)
    _seed_wallet_and_model(engine, user_id="user-1", balance=Decimal("100"))
    override_engine(engine)
    monkeypatch.setenv("DATABASE_URL", str(engine.url))
    monkeypatch.setenv("REDIS_URL", "redis://example/0")
    monkeypatch.setenv("SIDECAR_INTERNAL_TOKENS", TOKEN)
    for key, value in env_overrides.items():
        monkeypatch.setenv(key, value)
    get_settings.cache_clear()
    return TestClient(app)


def test_reserve_shadow_allows_disabled_model_passthrough(tmp_path, monkeypatch) -> None:
    client = _configure(tmp_path, monkeypatch, ENFORCEMENT_MODE="SHADOW")
    with client:
        response = client.post(
            "/reserve",
            headers=HEADERS,
            json={
                "user_id": "user-1",
                "trace_id": "trace-1",
                "idempotency_key": "shadow-1",
                "model": "disabled-model",
                "estimated_cost": "1.000000",
            },
        )
    assert response.status_code == 200


def test_reserve_enforce_denies_disabled_model(tmp_path, monkeypatch) -> None:
    client = _configure(tmp_path, monkeypatch, ENFORCEMENT_MODE="ENFORCE")
    with client:
        response = client.post(
            "/reserve",
            headers=HEADERS,
            json={
                "user_id": "user-1",
                "trace_id": "trace-1",
                "idempotency_key": "enforce-1",
                "model": "disabled-model",
                "estimated_cost": "1.000000",
            },
        )
    assert response.status_code == 403
