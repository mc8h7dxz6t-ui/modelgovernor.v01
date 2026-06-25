"""Append-only platform event audit — memory and Postgres."""
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from platforms.common.platform_store import append_platform_event, list_platform_events, reset_all_stores


@pytest.fixture(autouse=True)
def _reset():
    reset_all_stores()
    yield
    reset_all_stores()


def test_memory_append_only_events():
    append_platform_event("algofreeze", "ORDER_ROUTED", "ord-1", {"freeze_state": "ACTIVE"})
    append_platform_event("algofreeze", "EGRESS_BLOCKED", "ord-2", {"reason": "FROZEN"})
    events = list_platform_events("algofreeze")
    assert len(events) == 2
    assert events[0]["event_type"] == "EGRESS_BLOCKED"


def test_algofreeze_events_endpoint():
    from platforms.algofreeze.main import app

    client = TestClient(app)
    client.post(
        "/orders",
        json={"order_id": "evt-1", "runtime_sha": "wrong-sha"},
    )
    events = client.get("/events")
    assert events.status_code == 200
    body = events.json()
    assert any(e["event_type"] == "VERSION_MISMATCH_FREEZE" for e in body)


def test_wirematch_events_endpoint():
    from platforms.wire_match.main import app

    client = TestClient(app)
    client.post(
        "/wire/evaluate",
        json={
            "wire_id": "w-evt-1",
            "beneficiary_name": "Wrong Corp",
            "beneficiary_account": "US99",
            "reference": "x",
            "amount": "100.00",
        },
    )
    events = client.get("/events")
    assert events.status_code == 200
    assert len(events.json()) >= 1
