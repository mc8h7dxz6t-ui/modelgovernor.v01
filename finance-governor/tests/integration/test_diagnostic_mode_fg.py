"""Spine diagnostic mode — fail closed writes, fail open reads."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
SIDECAR = ROOT / "spine" / "sidecar"
sys.path.insert(0, str(SIDECAR))

FG_TESTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(FG_TESTS))

from conftest_spine import spine_db  # noqa: F401

HEADERS = {"x-internal-token": "test-token"}


@pytest.fixture()
def client(spine_db):
    from app.main import app

    return TestClient(app)


def test_diagnostic_blocks_crystallize_not_healthz(client):
    from app.diagnostic_mode import clear_diagnostic_mode, enter_diagnostic_mode

    clear_diagnostic_mode()
    enter_diagnostic_mode(component="test", reason="synthetic")

    health = client.get("/healthz")
    assert health.status_code == 200

    ready = client.get("/readyz")
    assert ready.status_code == 200
    assert ready.json()["details"]["diagnostic_mode"] is True

    blocked = client.post(
        "/crystallize",
        headers=HEADERS,
        json={
            "platform": "wire_match",
            "operation_id": "diag-1",
            "risk_tier": "low",
            "facets": {"amount": "1.00"},
        },
    )
    assert blocked.status_code == 503

    verify = client.get("/internal/decisions/verify-chain", headers=HEADERS)
    assert verify.status_code == 200

    clear_diagnostic_mode()


def test_diagnostic_clear_restores_writes(client):
    from app.diagnostic_mode import clear_diagnostic_mode, enter_diagnostic_mode

    enter_diagnostic_mode(component="test", reason="audit")
    client.post("/internal/diagnostic/clear", headers=HEADERS)
    clear_diagnostic_mode()

    ok = client.post(
        "/crystallize",
        headers=HEADERS,
        json={
            "platform": "wire_match",
            "operation_id": "diag-2",
            "risk_tier": "low",
            "facets": {"amount": "2.00"},
        },
    )
    assert ok.status_code == 200
