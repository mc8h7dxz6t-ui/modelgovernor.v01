"""All standalone platforms — health and core API smoke."""
from __future__ import annotations

import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def test_all_platforms_health_and_core_apis():
    from platforms.egress_lock.main import app as egress_app
    from platforms.identity_gate.main import app as identity_app
    from platforms.lineage_ingest.main import app as lineage_app
    from platforms.witness_bridge.main import app as witness_app

    identity = TestClient(identity_app)
    assert identity.get("/healthz").status_code == 200
    arm = identity.post(
        "/session/arm",
        json={
            "session_id": "p1",
            "user_id": "alice@corp.example",
            "device_fingerprint": "dev_fp_trusted_workstation",
            "client_ip": "10.0.1.1",
        },
    )
    assert arm.json()["decision"] == "AUTHORIZED"

    egress = TestClient(egress_app)
    assert egress.get("/healthz").status_code == 200
    ev = egress.post(
        "/egress/evaluate",
        json={
            "egress_id": "e1",
            "principal_id": "alice@corp.example",
            "destination": "s3://corp-backup",
            "byte_count": 512,
        },
    )
    assert ev.json()["decision"] == "ALLOWED"

    witness = TestClient(witness_app)
    assert witness.get("/healthz").status_code == 200
    witness.post(
        "/ingest/generic",
        json={"principal_id": "alice", "event_type": "login", "severity": "standard"},
    )

    lineage = TestClient(lineage_app)
    assert lineage.get("/healthz").status_code == 200
    lineage.post(
        "/ingest/falco",
        json={
            "rule": "Write below binary dir",
            "priority": "Notice",
            "output_fields": {"proc.name": "vim", "user.name": "alice"},
        },
    )
