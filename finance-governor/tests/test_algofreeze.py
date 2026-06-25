"""AlgoFreeze platform tests."""
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from platforms.algofreeze.main import app


@pytest.fixture()
def client():
    return TestClient(app)


def test_order_routes_when_active(client):
    r = client.post("/orders", json={"order_id": "o1", "runtime_sha": "approved-sha-v1"})
    assert r.status_code == 200
    assert r.json()["status"] == "ROUTED"


def test_version_mismatch_freezes_and_blocks(client):
    bad = client.post("/orders", json={"order_id": "o2", "runtime_sha": "wrong-sha"})
    assert bad.status_code == 403
    assert "VERSION_MISMATCH" in bad.json()["detail"]
    blocked = client.post("/orders", json={"order_id": "o3", "runtime_sha": "approved-sha-v1"})
    assert blocked.status_code == 403
    assert "FROZEN" in blocked.json()["detail"]
    assert client.get("/status").json()["freeze_state"] == "FROZEN"


def test_feed_degraded_blocks_order(client):
    from time import monotonic

    from platforms.algofreeze import main as af_main

    af_main._feed._last_packet_at = monotonic() - 10
    r = client.post("/orders", json={"order_id": "feed-1", "runtime_sha": "approved-sha-v1"})
    assert r.status_code == 403
    assert "FEED_DEGRADED" in r.json()["detail"]


def test_no_egress_when_frozen(client):
    client.post("/orders", json={"order_id": "o4", "runtime_sha": "bad"})
    status = client.get("/status").json()
    assert status["blocked_egress_attempts"] >= 1
