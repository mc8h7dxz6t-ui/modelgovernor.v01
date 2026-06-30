"""WireMatch hero wedge — golden-record mismatch → HELD + platform event (Phase A3)."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from platforms.wire_match.main import app


@pytest.fixture()
def client():
    return TestClient(app)


def test_golden_record_beneficiary_mismatch_held_with_chain_evidence(client):
    """Beneficiary mismatch must HELD wire and record platform event (chain row when spine up)."""
    r = client.post(
        "/wire/evaluate",
        json={
            "wire_id": "hero-held-1",
            "beneficiary_name": "Totally Wrong Corp",
            "beneficiary_account": "US99WRONG",
            "reference": "payment",
            "amount": "7800000.00",
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["decision"] == "HELD"
    assert body["reason"] == "BENEFICIARY_MISMATCH"

    events = client.get("/events").json()
    held = [e for e in events if e.get("event_type") == "HELD" and e.get("operation_id") == "hero-held-1"]
    assert held, "expected HELD platform event for examiner chain evidence"
    assert held[0].get("metadata", {}).get("reason") == "BENEFICIARY_MISMATCH"


def test_amount_anomaly_held_records_event(client):
    r = client.post(
        "/wire/evaluate",
        json={
            "wire_id": "hero-held-2",
            "beneficiary_name": "Revlon Lenders Group",
            "beneficiary_account": "US12REV001",
            "reference": "loan payment",
            "amount": "900000000.00",
        },
    )
    assert r.json()["decision"] == "HELD"
    assert r.json()["reason"] == "AMOUNT_ANOMALY"
