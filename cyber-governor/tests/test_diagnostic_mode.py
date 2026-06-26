"""Diagnostic mode — write halt, read continue."""
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


def test_diagnostic_blocks_crystallize(client):
    from app.diagnostic_mode import clear_diagnostic_mode, enter_diagnostic_mode

    enter_diagnostic_mode(component="test", reason="unit test")
    r = client.post(
        "/crystallize",
        headers=HEADERS,
        json={
            "platform": "identity_gate",
            "operation_id": "diag-1",
            "risk_tier": "critical",
            "facets": {"session_state": "AUTHORIZED"},
        },
    )
    assert r.status_code == 503
    clear_diagnostic_mode()

    ok = client.get("/internal/diagnostic/status", headers=HEADERS)
    assert ok.json()["diagnostic_mode"] is False

    reads = client.get("/internal/security/verify-chain", headers=HEADERS)
    assert reads.status_code == 200
