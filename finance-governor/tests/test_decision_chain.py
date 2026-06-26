"""Decision event hash chain verification."""
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


def test_decision_chain_valid_after_lifecycle(client):
    facets = {"amount": "100.00", "currency": "USD"}
    r = client.post(
        "/crystallize",
        headers=HEADERS,
        json={
            "platform": "wire_match",
            "operation_id": "chain-1",
            "risk_tier": "high",
            "facets": facets,
        },
    )
    crystal_id = r.json()["crystal_id"]
    client.post(
        "/commit",
        headers=HEADERS,
        json={"crystal_id": crystal_id, "facets": facets, "committed_exposure": "0"},
    )
    verify = client.get("/internal/decisions/verify-chain", headers=HEADERS)
    assert verify.status_code == 200
    body = verify.json()
    assert body["valid"] is True
    assert body["sealed_count"] >= 2
    assert body["unsealed_count"] == 0


def test_decision_chain_detects_tamper(client, spine_db):
    from sqlalchemy import text

    from app.db import get_db_session

    facets = {"amount": "50.00"}
    r = client.post(
        "/crystallize",
        headers=HEADERS,
        json={"platform": "wire_match", "operation_id": "chain-tamper", "risk_tier": "high", "facets": facets},
    )
    with get_db_session() as session:
        session.execute(text("UPDATE decision_events SET row_hash = :bad WHERE event_id = 1"), {"bad": "f" * 64})
        session.commit()

    verify = client.get("/internal/decisions/verify-chain", headers=HEADERS)
    body = verify.json()
    assert body["valid"] is False
    assert body["first_break"] is not None
