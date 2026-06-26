"""Chaos-style resilience — Finance Governor standalone (no ModelGovernor harness)."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
SIDECAR = ROOT / "spine" / "sidecar"
sys.path.insert(0, str(SIDECAR))

from tests.conftest_spine import spine_db  # noqa: F401

HEADERS = {"x-internal-token": "test-token"}


@pytest.fixture()
def client(spine_db):
    from app.main import app

    return TestClient(app)


def test_reads_survive_diagnostic_write_halt(client):
    from app.diagnostic_mode import enter_diagnostic_mode

    facets = {"amount": "10.00"}
    ok = client.post(
        "/crystallize",
        headers=HEADERS,
        json={"platform": "wire_match", "operation_id": "chaos-1", "risk_tier": "high", "facets": facets},
    )
    assert ok.status_code == 200

    enter_diagnostic_mode(component="chaos-test", reason="simulated invariant breach")
    blocked = client.post(
        "/crystallize",
        headers=HEADERS,
        json={"platform": "wire_match", "operation_id": "chaos-2", "risk_tier": "high", "facets": facets},
    )
    assert blocked.status_code == 503

    verify = client.get("/internal/decisions/verify-chain", headers=HEADERS)
    assert verify.status_code == 200
    assert verify.json()["sealed_count"] >= 1

    client.post("/internal/diagnostic/clear", headers=HEADERS)
