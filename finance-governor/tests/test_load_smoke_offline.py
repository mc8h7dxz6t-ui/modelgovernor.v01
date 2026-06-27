"""Offline load smoke — repeated crystallize/commit without live spine."""
from __future__ import annotations

import sys
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
SIDECAR = ROOT / "spine" / "sidecar"
sys.path.insert(0, str(SIDECAR))

from tests.conftest_spine import spine_db  # noqa: F401

HEADERS = {"x-internal-token": "test-token"}


def _one_lifecycle(client: TestClient, worker_id: int) -> None:
    op_id = f"load-offline-{worker_id}-{uuid.uuid4().hex[:8]}"
    facets = {"amount": "1.00", "worker": worker_id}
    r = client.post(
        "/crystallize",
        headers=HEADERS,
        json={"platform": "wire_match", "operation_id": op_id, "risk_tier": "high", "facets": facets},
    )
    assert r.status_code == 200, r.text
    crystal_id = r.json()["crystal_id"]
    c = client.post(
        "/commit",
        headers=HEADERS,
        json={"crystal_id": crystal_id, "facets": facets, "committed_exposure": "0"},
    )
    assert c.status_code == 200, c.text


def test_repeated_crystallize_commit_offline(spine_db):
    from app.main import app

    client = TestClient(app)
    total = 12
    for i in range(total):
        _one_lifecycle(client, i)

    verify = client.get("/internal/decisions/verify-chain", headers=HEADERS)
    assert verify.status_code == 200
    body = verify.json()
    assert body["valid"] is True
    assert body["sealed_count"] >= total * 2
