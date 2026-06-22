from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
import sys

from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from reconciler.app.sweeper import sweep_expired_reservations
from sidecar.app.config import get_settings
from sidecar.app.db import override_engine
from sidecar.app.main import app
from tests.integration.test_ledger_hardening import _bootstrap_schema, _create_test_engine, _seed_wallet_and_model

TOKEN = "test-token"
HEADERS = {"x-internal-token": TOKEN}


def test_internal_admin_routes_require_auth(tmp_path, monkeypatch) -> None:
    _configure_sidecar_env(tmp_path, monkeypatch)

    with TestClient(app) as client:
        assert client.get("/internal/wallet/user-1").status_code == 401
        assert client.get("/internal/operation/op-1").status_code == 401
        assert client.get("/internal/events/recent").status_code == 401
        assert client.get("/metrics").status_code == 401


def test_admin_read_surfaces_and_metrics_expose_governance_state(tmp_path, monkeypatch) -> None:
    engine = _configure_sidecar_env(tmp_path, monkeypatch)

    with TestClient(app) as client:
        _reserve(client, "op-expired", "trace-expired")
        _force_expiry(engine, "op-expired")
        with Session(engine) as session:
            assert sweep_expired_reservations(session, batch_size=10) == 1

        _reserve(client, "op-stranded", "trace-stranded")
        _in_flight(client, "op-stranded", "provider-stranded", "attempt-stranded")
        _force_expiry(engine, "op-stranded")
        with Session(engine) as session:
            assert sweep_expired_reservations(session, batch_size=10) == 1

        _reserve(client, "op-settle", "trace-settle")
        _in_flight(client, "op-settle", "provider-settle", "attempt-settle")
        _settle(client, "op-settle", "provider-settle", "attempt-settle", Decimal("11.000000"))

        wallet = client.get("/internal/wallet/user-1", headers=HEADERS)
        assert wallet.status_code == 200
        wallet_payload = wallet.json()
        assert wallet_payload["active"] is False
        assert wallet_payload["lock_reason"] == "DRIFT_THRESHOLD_EXCEEDED"

        operation = client.get("/internal/operation/op-settle", headers=HEADERS)
        assert operation.status_code == 200
        op_payload = operation.json()
        assert op_payload["status"] == "SETTLED"
        assert op_payload["terminal_reason"] == "SETTLED_FINAL"
        assert op_payload["provider_request_id"] == "provider-settle"
        assert op_payload["attempts"][0]["attempt_key"] == "attempt-settle"

        by_provider = client.get("/internal/operation/by-provider/provider-settle", headers=HEADERS)
        assert by_provider.status_code == 200
        assert by_provider.json()["idempotency_key"] == "op-settle"

        trace = client.get("/internal/trace/trace-settle", headers=HEADERS)
        assert trace.status_code == 200
        trace_payload = trace.json()
        assert Decimal(trace_payload["reserved_total"]) == Decimal("0.000000")
        assert Decimal(trace_payload["settled_total"]) == Decimal("11.000000")

        events = client.get("/internal/events/recent?limit=20", headers=HEADERS)
        assert events.status_code == 200
        event_payload = events.json()["events"]
        assert len(event_payload) >= 6
        assert isinstance(event_payload[0]["metadata"], dict)
        event_types = {event["event_type"] for event in event_payload}
        assert {"EXPIRED_SWEEP", "STRANDED_HOLD", "DRIFT_ENFORCED", "SETTLED_FINAL"}.issubset(event_types)

        metrics = client.get("/metrics", headers=HEADERS)
        assert metrics.status_code == 200
        body = metrics.text
        assert 'modelgovernor_ledger_events_total{event_type="RESERVE_CREATED"} 3' in body
        assert 'modelgovernor_drift_events_total{state="enforced"} 1' in body
        assert 'modelgovernor_failure_events_total{event_type="STRANDED_HOLD"} 1' in body
        assert 'modelgovernor_reconciliation_events_total{event_type="EXPIRED_SWEEP"} 1' in body
        assert 'modelgovernor_operations_total{status="SETTLED"} 1' in body
        assert 'modelgovernor_operations_total{status="STRANDED"} 1' in body


def _configure_sidecar_env(tmp_path, monkeypatch):
    db_path = tmp_path / "sidecar_observability.sqlite3"
    engine = _create_test_engine(db_path)
    _bootstrap_schema(engine)
    _seed_wallet_and_model(engine, user_id="user-1", balance=Decimal("100.000000"))

    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("REDIS_URL", "redis://example/0")
    monkeypatch.setenv("SIDECAR_INTERNAL_TOKENS", TOKEN)

    get_settings.cache_clear()
    override_engine(engine)
    return engine


def _reserve(client: TestClient, operation_key: str, trace_id: str) -> None:
    response = client.post(
        "/reserve",
        headers=HEADERS,
        json={
            "user_id": "user-1",
            "trace_id": trace_id,
            "idempotency_key": operation_key,
            "model": "gpt-4o-mini",
            "estimated_cost": "10.000000",
        },
    )
    assert response.status_code == 200


def _in_flight(
    client: TestClient, operation_key: str, provider_request_id: str, dispatch_attempt_key: str
) -> None:
    response = client.post(
        "/settle",
        headers=HEADERS,
        json={
            "idempotency_key": operation_key,
            "outcome": "IN_FLIGHT",
            "dispatch_attempt_key": dispatch_attempt_key,
            "provider_name": "openai",
            "model": "gpt-4o-mini",
            "provider_request_id": provider_request_id,
        },
    )
    assert response.status_code == 200


def _settle(
    client: TestClient,
    operation_key: str,
    provider_request_id: str,
    dispatch_attempt_key: str,
    actual_cost: Decimal,
) -> None:
    response = client.post(
        "/settle",
        headers=HEADERS,
        json={
            "idempotency_key": operation_key,
            "outcome": "SETTLED",
            "actual_cost": str(actual_cost),
            "dispatch_attempt_key": dispatch_attempt_key,
            "provider_name": "openai",
            "model": "gpt-4o-mini",
            "provider_request_id": provider_request_id,
        },
    )
    assert response.status_code == 200


def _force_expiry(engine, operation_key: str) -> None:
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                UPDATE escrow_ledger
                SET expires_at = :expired_at
                WHERE idempotency_key = :idempotency_key
                """
            ),
            {
                "expired_at": datetime.now(timezone.utc) - timedelta(minutes=2),
                "idempotency_key": operation_key,
            },
        )
