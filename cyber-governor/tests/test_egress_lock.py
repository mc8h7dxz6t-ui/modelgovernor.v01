"""EgressLock platform tests."""
from __future__ import annotations

import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from platforms.egress_lock.main import app  # noqa: E402


def test_egress_allowed():
    client = TestClient(app)
    r = client.post(
        "/egress/evaluate",
        json={
            "egress_id": "e1",
            "principal_id": "alice@corp.example",
            "destination": "s3://corp-backup",
            "byte_count": 4096,
        },
    )
    assert r.status_code == 200
    assert r.json()["decision"] == "ALLOWED"


def test_egress_blocked_destination():
    client = TestClient(app)
    r = client.post(
        "/egress/evaluate",
        json={
            "egress_id": "e2",
            "principal_id": "alice@corp.example",
            "destination": "evil-exfil.example",
            "byte_count": 1024,
        },
    )
    assert r.status_code == 200
    assert r.json()["decision"] == "BLOCKED"
