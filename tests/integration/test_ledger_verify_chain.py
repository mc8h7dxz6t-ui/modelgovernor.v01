"""Ledger hash-chain verification API and integrity logic tests."""
from __future__ import annotations

from decimal import Decimal
from pathlib import Path
import sys

from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from sidecar.app.config import get_settings
from sidecar.app.db import override_engine
from sidecar.app.ledger import reserve_operation
from sidecar.app.ledger_seal import GENESIS_HASH, verify_ledger_chain
from sidecar.app.main import app
from sidecar.app.schemas import ReserveRequest
from tests.integration.test_ledger_hardening import _bootstrap_schema, _create_test_engine, _seed_wallet_and_model, _settings

TOKEN = "test-token"
HEADERS = {"x-internal-token": TOKEN}


def _configure(tmp_path, monkeypatch):
    engine = _create_test_engine(tmp_path / "ledger-verify.sqlite3")
    _bootstrap_schema(engine)
    _seed_wallet_and_model(engine, user_id="user-1")
    monkeypatch.setenv("DATABASE_URL", str(engine.url))
    monkeypatch.setenv("REDIS_URL", "redis://example/0")
    monkeypatch.setenv("SIDECAR_INTERNAL_TOKENS", TOKEN)
    get_settings.cache_clear()
    override_engine(engine)
    return engine


def test_verify_chain_endpoint_reports_valid_sealed_events(tmp_path, monkeypatch) -> None:
    engine = _configure(tmp_path, monkeypatch)
    settings = _settings(engine)

    with Session(engine) as session:
        reserve_operation(
            session,
            settings,
            ReserveRequest(
                user_id="user-1",
                trace_id="trace-1",
                idempotency_key="op-verify",
                model="gpt-4o-mini",
                estimated_cost=Decimal("1.000000"),
            ),
        )
        session.commit()

    with Session(engine) as session:
        result = verify_ledger_chain(session)
        assert result.valid is True
        assert result.sealed_count == 1
        assert result.unsealed_count == 0

    with TestClient(app) as client:
        response = client.get("/internal/ledger/verify-chain", headers=HEADERS)
        assert response.status_code == 200
        body = response.json()
        assert body["valid"] is True
        assert body["sealed_count"] == 1
        assert body["unsealed_count"] == 0


def test_verify_chain_endpoint_fails_on_tampered_row(tmp_path, monkeypatch) -> None:
    engine = _configure(tmp_path, monkeypatch)
    settings = _settings(engine)

    with Session(engine) as session:
        reserve_operation(
            session,
            settings,
            ReserveRequest(
                user_id="user-1",
                trace_id="trace-2",
                idempotency_key="op-tamper",
                model="gpt-4o-mini",
                estimated_cost=Decimal("2.000000"),
            ),
        )
        session.execute(
            text(
                """
                UPDATE ledger_events
                SET prev_hash = :prev_hash, row_hash = :row_hash
                WHERE idempotency_key = 'op-tamper'
                """
            ),
            {"prev_hash": GENESIS_HASH, "row_hash": "f" * 64},
        )
        session.commit()

    with TestClient(app) as client:
        response = client.get("/internal/ledger/verify-chain", headers=HEADERS)
        assert response.status_code == 422
        body = response.json()
        assert body["detail"]["valid"] is False


def test_verify_chain_requires_auth(tmp_path, monkeypatch) -> None:
    _configure(tmp_path, monkeypatch)
    with TestClient(app) as client:
        assert client.get("/internal/ledger/verify-chain").status_code == 401
