"""AlgoFreeze hero wedge — EMS version mismatch → desk freeze (Phase A2)."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import platforms.algofreeze.main as af_main
from platforms.algofreeze.feed_heartbeat import FeedHeartbeat
from platforms.algofreeze.freeze_controller import FreezeController, VersionRegistry
from platforms.algofreeze.order_gate import OrderGate
from platforms.algofreeze.main import app


@pytest.fixture(autouse=True)
def reset_algofreeze_state():
    af_main._registry = VersionRegistry(approved_sha="approved-sha-v1")
    af_main._controller = FreezeController()
    af_main._gate = OrderGate(af_main._controller)
    af_main._feed = FeedHeartbeat(max_gap_seconds=2.0)
    yield


@pytest.fixture()
def client():
    return TestClient(app)


def test_ems_version_mismatch_freezes_desk_and_blocks_subsequent_orders(client):
    """Approved SHA mismatch simulates bad EMS deploy — desk must freeze with 403."""
    mismatch = client.post(
        "/orders",
        json={"order_id": "ems-bad-deploy", "runtime_sha": "wrong-deploy-sha"},
    )
    assert mismatch.status_code == 403
    assert "VERSION_MISMATCH" in mismatch.json()["detail"]

    status = client.get("/status").json()
    assert status["freeze_state"] == "FROZEN"

    blocked = client.post(
        "/orders",
        json={"order_id": "ems-after-freeze", "runtime_sha": "approved-sha-v1"},
    )
    assert blocked.status_code == 403
    assert "FROZEN" in blocked.json()["detail"]
    assert client.get("/status").json()["blocked_egress_attempts"] >= 1


def test_ems_approved_sha_routes_when_feed_healthy(client):
    client.post("/admin/feed-packet")
    ok = client.post(
        "/orders",
        json={"order_id": "ems-good", "runtime_sha": "approved-sha-v1"},
    )
    assert ok.status_code == 200
    assert ok.json()["status"] == "ROUTED"


def test_algofreeze_events_record_freeze(client):
    client.post("/orders", json={"order_id": "evt-1", "runtime_sha": "bad-sha"})
    events = client.get("/events").json()
    types = {e.get("event_type") for e in events}
    assert "VERSION_MISMATCH_FREEZE" in types
