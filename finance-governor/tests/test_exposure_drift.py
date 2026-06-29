"""Exposure drift lockout tests."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[1]
SIDECAR = ROOT / "spine" / "sidecar"
sys.path.insert(0, str(SIDECAR))

from tests.conftest_spine import spine_db  # noqa: F401

HEADERS = {"x-internal-token": "test-token"}


@pytest.fixture()
def client(spine_db):
    from app.main import app

    return TestClient(app)


def test_drift_within_tolerance_no_lock(client, spine_db):
    facets = {"amount": "100.00", "desk_id": "desk-default"}
    r = client.post(
        "/crystallize",
        headers=HEADERS,
        json={
            "platform": "wire_match",
            "operation_id": "drift-tolerated-1",
            "account_id": "desk-default",
            "risk_tier": "high",
            "facets": facets,
            "policy_id": "wire-critical-us",
            "reserved_exposure": "100.00",
        },
    )
    crystal_id = r.json()["crystal_id"]
    c = client.post(
        "/commit",
        headers=HEADERS,
        json={"crystal_id": crystal_id, "facets": facets, "committed_exposure": "100.25"},
    )
    assert c.status_code == 200
    with spine_db.begin() as conn:
        row = conn.execute(
            text("SELECT active FROM account_ledgers WHERE account_id = 'desk-default'")
        ).first()
    assert row[0] in (True, 1)


def test_drift_exceeds_tolerance_locks_account(client, spine_db):
    facets = {"amount": "100.00", "desk_id": "desk-default"}
    r = client.post(
        "/crystallize",
        headers=HEADERS,
        json={
            "platform": "wire_match",
            "operation_id": "drift-enforced-1",
            "account_id": "desk-default",
            "risk_tier": "high",
            "facets": facets,
            "policy_id": "wire-critical-us",
            "reserved_exposure": "100.00",
        },
    )
    crystal_id = r.json()["crystal_id"]
    c = client.post(
        "/commit",
        headers=HEADERS,
        json={"crystal_id": crystal_id, "facets": facets, "committed_exposure": "200.00"},
    )
    assert c.status_code == 200
    with spine_db.begin() as conn:
        row = conn.execute(
            text(
                "SELECT active, lock_reason FROM account_ledgers WHERE account_id = 'desk-default'"
            )
        ).first()
    assert row[0] in (False, 0)
    assert row[1] == "DRIFT_THRESHOLD_EXCEEDED"


def test_drift_records_guardrail_incident(client):
    facets = {"amount": "50.00"}
    r = client.post(
        "/crystallize",
        headers=HEADERS,
        json={
            "platform": "wire_match",
            "operation_id": "drift-guardrail-1",
            "account_id": "desk-default",
            "risk_tier": "high",
            "facets": facets,
            "reserved_exposure": "50.00",
        },
    )
    crystal_id = r.json()["crystal_id"]
    client.post(
        "/commit",
        headers=HEADERS,
        json={"crystal_id": crystal_id, "facets": facets, "committed_exposure": "100.00"},
    )
    incidents = client.get("/internal/guardrail/incidents", headers=HEADERS)
    assert incidents.status_code == 200
    assert any(i["incident_type"] == "DRIFT_THRESHOLD_EXCEEDED" for i in incidents.json())


def test_drift_tolerance_helper():
    from decimal import Decimal

    from app.config import Settings
    from app.exposure_drift import drift_exceeds_tolerance

    settings = Settings()
    assert drift_exceeds_tolerance(Decimal("0.25"), Decimal("100"), settings) is False
    assert drift_exceeds_tolerance(Decimal("10"), Decimal("100"), settings) is True
