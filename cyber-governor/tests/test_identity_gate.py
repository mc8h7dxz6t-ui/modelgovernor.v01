"""IdentityGate platform tests."""
from __future__ import annotations

import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from platforms.identity_gate.main import app  # noqa: E402


def test_session_arm_authorized():
    client = TestClient(app)
    r = client.post(
        "/session/arm",
        json={
            "session_id": "s1",
            "user_id": "alice@corp.example",
            "device_fingerprint": "dev_fp_trusted_workstation",
            "client_ip": "10.0.1.42",
        },
    )
    assert r.status_code == 200
    assert r.json()["decision"] == "AUTHORIZED"


def test_session_arm_stranded_on_hijack():
    client = TestClient(app)
    r = client.post(
        "/session/arm",
        json={
            "session_id": "s2",
            "user_id": "alice@corp.example",
            "device_fingerprint": "attacker_device",
            "client_ip": "203.0.113.9",
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["decision"] == "STRANDED"
    assert body["session_state"] == "STRANDED"
