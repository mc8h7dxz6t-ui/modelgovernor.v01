"""Regulatory export and attribution API tests."""
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


def test_regulatory_export_shape(client):
    r = client.get("/internal/regulatory/export?limit=5", headers=HEADERS)
    assert r.status_code == 200
    body = r.json()
    assert "chain_verification" in body
    assert "crystals" in body
    assert "decision_events" in body
    assert "guardrail_incidents" in body
    assert body["chain_verification"]["valid"] is True


def test_attribution_summary_empty(client):
    r = client.get("/internal/attribution/summary", headers=HEADERS)
    assert r.status_code == 200
    body = r.json()
    assert "by_desk" in body
    assert "by_platform" in body


def test_attribution_after_commit(client):
    facets = {"amount": "1000.00", "desk_id": "desk-alpha"}
    cry = client.post(
        "/crystallize",
        headers=HEADERS,
        json={
            "platform": "wire_match",
            "operation_id": "attr-1",
            "account_id": "desk-default",
            "risk_tier": "high",
            "facets": facets,
            "reserved_exposure": "1000.00",
        },
    )
    crystal_id = cry.json()["crystal_id"]
    client.post(
        "/commit",
        headers=HEADERS,
        json={"crystal_id": crystal_id, "facets": facets, "committed_exposure": "1000.00"},
    )
    attr = client.get("/internal/attribution/summary", headers=HEADERS)
    desks = {d["desk_id"]: d for d in attr.json()["by_desk"]}
    assert "desk-alpha" in desks
    assert desks["desk-alpha"]["commit_count"] == 1


def test_guardrail_incidents_endpoint(client):
    r = client.get("/internal/guardrail/incidents", headers=HEADERS)
    assert r.status_code == 200
    assert isinstance(r.json(), list)
