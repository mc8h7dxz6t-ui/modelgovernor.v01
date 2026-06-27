"""SubledgerSync platform tests."""
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from platforms.subledger_sync.main import app, reset_state


@pytest.fixture(autouse=True)
def reset_state_fixture():
    reset_state()
    yield
    reset_state()


@pytest.fixture()
def client():
    return TestClient(app)


def test_healthz(client):
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_ingest_transaction(client):
    r = client.post(
        "/transactions",
        json={
            "entity_id": "UK-01",
            "counterparty_id": "US-01",
            "amount": "10000.00",
            "currency": "USD",
            "value_date": "2026-06-01",
        },
    )
    assert r.status_code == 200
    assert r.json()["pending_count"] == 1


def test_mirrored_pair_matched(client):
    client.post(
        "/transactions",
        json={
            "entity_id": "UK-01",
            "counterparty_id": "US-01",
            "amount": "10000.00",
            "currency": "USD",
            "value_date": "2026-06-01",
        },
    )
    r = client.post(
        "/match/run",
        json={
            "entity_id": "US-01",
            "counterparty_id": "UK-01",
            "amount": "10000.00",
            "currency": "USD",
            "value_date": "2026-06-01",
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "MATCHED"
    assert body["mirror_hash"] is not None
    assert body["fx_hash"] is not None


def test_unmatched_emits_discrepancy(client):
    r = client.post(
        "/match/run",
        json={
            "entity_id": "DE-01",
            "counterparty_id": "FR-01",
            "amount": "500.00",
            "currency": "USD",
            "value_date": "2026-06-01",
        },
    )
    assert r.json()["status"] == "DISCREPANCY"
    disc = client.get("/discrepancies")
    assert len(disc.json()) == 1


def test_fx_drift_flagged(client):
    client.post(
        "/transactions",
        json={
            "entity_id": "UK-01",
            "counterparty_id": "US-01",
            "amount": "10000.00",
            "currency": "USD",
            "value_date": "2026-06-01",
        },
    )
    r = client.post(
        "/match/run",
        json={
            "entity_id": "US-01",
            "counterparty_id": "UK-01",
            "amount": "15000.00",
            "currency": "USD",
            "value_date": "2026-06-01",
        },
    )
    assert r.json()["status"] == "DISCREPANCY"
    assert r.json()["reason"] == "NO_MIRROR_OR_FX_DRIFT"
