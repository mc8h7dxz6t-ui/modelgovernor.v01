"""Diagnostic mode write-path blocking and Redis cluster propagation."""
from __future__ import annotations

from decimal import Decimal
from pathlib import Path
import sys

import pytest
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

fakeredis = pytest.importorskip("fakeredis")

from sidecar.app.config import get_settings
from sidecar.app.db import override_engine
from sidecar.app.diagnostic_mode import clear_diagnostic_mode, enter_diagnostic_mode, is_diagnostic_mode
from sidecar.app.main import app
from tests.integration.test_ledger_hardening import _bootstrap_schema, _create_test_engine, _seed_wallet_and_model

TOKEN = "test-token"
HEADERS = {"x-internal-token": TOKEN}


def _configure(tmp_path, monkeypatch):
    engine = _create_test_engine(tmp_path / "diag-block.sqlite3")
    _bootstrap_schema(engine)
    _seed_wallet_and_model(engine, user_id="user-1")
    monkeypatch.setenv("DATABASE_URL", str(engine.url))
    monkeypatch.setenv("REDIS_URL", "redis://fake/0")
    monkeypatch.setenv("SIDECAR_INTERNAL_TOKENS", TOKEN)
    get_settings.cache_clear()
    override_engine(engine)
    fake = fakeredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr("redis.from_url", lambda *args, **kwargs: fake)
    return fake


def test_diagnostic_mode_blocks_reserve_and_settle(tmp_path, monkeypatch) -> None:
    _configure(tmp_path, monkeypatch)
    clear_diagnostic_mode()
    enter_diagnostic_mode(component="test", reason="synthetic")

    with TestClient(app) as client:
        reserve = client.post(
            "/reserve",
            headers=HEADERS,
            json={
                "user_id": "user-1",
                "trace_id": "trace-diag",
                "idempotency_key": "op-diag",
                "model": "gpt-4o-mini",
                "estimated_cost": "1.000000",
            },
        )
        assert reserve.status_code == 503

        settle = client.post(
            "/settle",
            headers=HEADERS,
            json={
                "idempotency_key": "op-diag",
                "outcome": "SETTLED",
                "actual_cost": "1.000000",
            },
        )
        assert settle.status_code == 503


def test_diagnostic_mode_propagates_via_redis(tmp_path, monkeypatch) -> None:
    _configure(tmp_path, monkeypatch)
    clear_diagnostic_mode()
    enter_diagnostic_mode(component="reconciler", reason="finance audit failure")
    assert is_diagnostic_mode() is True
    clear_diagnostic_mode()
