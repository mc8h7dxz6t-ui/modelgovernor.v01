"""Diagnostic mode write halt."""
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


def test_diagnostic_mode_blocks_crystallize(client):
    from app.diagnostic_mode import enter_diagnostic_mode

    enter_diagnostic_mode(component="test", reason="unit test")
    r = client.post(
        "/crystallize",
        headers=HEADERS,
        json={
            "platform": "wire_match",
            "operation_id": "diag-1",
            "risk_tier": "high",
            "facets": {"amount": "1.00"},
        },
    )
    assert r.status_code == 503
    assert "diagnostic mode" in r.json()["detail"]

    status = client.get("/internal/diagnostic/status", headers=HEADERS)
    assert status.json()["diagnostic_mode"] is True

    client.post("/internal/diagnostic/clear", headers=HEADERS)
    ok = client.post(
        "/crystallize",
        headers=HEADERS,
        json={
            "platform": "wire_match",
            "operation_id": "diag-2",
            "risk_tier": "high",
            "facets": {"amount": "1.00"},
        },
    )
    assert ok.status_code == 200
