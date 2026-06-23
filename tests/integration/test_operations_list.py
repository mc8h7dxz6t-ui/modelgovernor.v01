"""List operations admin endpoint tests."""
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


def _configure(tmp_path: Path, monkeypatch) -> TestClient:
    engine = _create_test_engine(tmp_path / "ops.sqlite3")
    _bootstrap_schema(engine)
    _seed_wallet_and_model(engine, user_id="ops-user", balance=Decimal("100"))
    override_engine(engine)
    monkeypatch.setenv("DATABASE_URL", str(engine.url))
    monkeypatch.setenv("REDIS_URL", "redis://example/0")
    monkeypatch.setenv("SIDECAR_INTERNAL_TOKENS", TOKEN)
    get_settings.cache_clear()
    return TestClient(app)


def test_list_operations_endpoint(tmp_path, monkeypatch) -> None:
    client = _configure(tmp_path, monkeypatch)
    client.post(
        "/reserve",
        headers=HEADERS,
        json={
            "user_id": "ops-user",
            "trace_id": "ops-trace",
            "idempotency_key": "ops-1",
            "model": "gpt-4o-mini",
            "estimated_cost": "10.000000",
        },
    )
    response = client.get("/internal/operations?status=RESERVED", headers=HEADERS)
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["operations"][0]["idempotency_key"] == "ops-1"
