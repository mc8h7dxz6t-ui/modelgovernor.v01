"""Threat Mesh — STRANDED identity blocks egress commit."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
SIDECAR = ROOT / "spine" / "sidecar"
sys.path.insert(0, str(SIDECAR))

from sqlalchemy import text

from tests.conftest_spine import spine_db  # noqa: F401

HEADERS = {"x-internal-token": "test-token"}


@pytest.fixture()
def client(spine_db):
    from app.main import app

    return TestClient(app)


def test_mesh_blocks_egress_when_identity_stranded(client, spine_db):
    with spine_db.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO threat_crystals (
                    crystal_id, platform, operation_id, risk_tier, facets,
                    request_fingerprint, crystal_hash, horizon_expires_at, terminal_state
                ) VALUES (
                    'tcrys_mesh_parent', 'identity_gate', 'sess-mesh-1', 'critical',
                    :facets, 'fp', 'hash1', datetime('now', '+1 hour'), NULL
                )
                """
            ),
            {"facets": json.dumps({"session_state": "STRANDED"})},
        )

    egress_facets = {"destination": "s3://corp", "byte_count": 100}
    cr = client.post(
        "/crystallize",
        headers=HEADERS,
        json={
            "platform": "egress_lock",
            "operation_id": "eg-mesh-1",
            "risk_tier": "critical",
            "facets": egress_facets,
        },
    )
    crystal_id = cr.json()["crystal_id"]
    blocked = client.post(
        "/commit",
        headers=HEADERS,
        json={"crystal_id": crystal_id, "facets": egress_facets, "outcome": "allowed"},
    )
    assert blocked.status_code == 409
    assert "mesh" in blocked.json()["detail"].lower()
