"""WitnessBridge platform tests."""
from __future__ import annotations

import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from platforms.common.integrations import normalize_event  # noqa: E402
from platforms.witness_bridge.main import app  # noqa: E402


def test_normalize_cloudtrail_delete():
    event = normalize_event(
        "cloudtrail",
        {"detail": {"eventName": "DeleteTrail", "eventID": "evt-1", "userIdentity": {"arn": "arn:aws:iam::1:user/a"}}},
    )
    assert event.severity == "critical"
    assert event.action == "DeleteTrail"


def test_ingest_cloudtrail():
    client = TestClient(app)
    r = client.post(
        "/ingest/cloudtrail",
        json={"detail": {"eventName": "DeleteTrail", "eventID": "evt-2", "userIdentity": {"arn": "arn:aws:iam::1:user/a"}}},
    )
    assert r.status_code == 200
    assert r.json()["severity"] == "critical"
