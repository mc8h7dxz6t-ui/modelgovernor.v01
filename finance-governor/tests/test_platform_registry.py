"""Platform registry runtime and adjudicate API."""
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


def test_list_registered_platforms(client):
    response = client.get("/internal/platforms", headers=HEADERS)
    assert response.status_code == 200
    names = {p["platform_name"] for p in response.json()}
    assert "wire_match" in names
    assert "credit_govern" in names


def test_unregistered_platform_rejected(client):
    response = client.post(
        "/crystallize",
        headers=HEADERS,
        json={
            "platform": "unknown_vendor",
            "operation_id": "x-1",
            "risk_tier": "high",
            "facets": {"amount": "1.00"},
        },
    )
    assert response.status_code == 422
    assert "not registered" in response.json()["detail"]


def test_facet_validation_on_crystallize(client):
    response = client.post(
        "/crystallize",
        headers=HEADERS,
        json={
            "platform": "wire_match",
            "operation_id": "facet-miss-1",
            "risk_tier": "high",
            "facets": {"currency": "USD"},
        },
    )
    assert response.status_code == 422
    assert "amount" in response.json()["detail"]


def test_adjudicate_strand(client):
    facets = {"amount": "50.00"}
    created = client.post(
        "/crystallize",
        headers=HEADERS,
        json={
            "platform": "wire_match",
            "operation_id": "strand-1",
            "risk_tier": "high",
            "facets": facets,
            "reserved_exposure": "10.00",
        },
    )
    crystal_id = created.json()["crystal_id"]
    stranded = client.post(
        "/adjudicate",
        headers=HEADERS,
        json={"crystal_id": crystal_id, "action": "strand", "reason": "manual_review"},
    )
    assert stranded.status_code == 200
    assert stranded.json()["status"] == "STRANDED"

    recon = client.get(f"/internal/crystals/{crystal_id}/reconstruct", headers=HEADERS)
    assert recon.json()["crystal"]["terminal_state"] == "STRANDED"
