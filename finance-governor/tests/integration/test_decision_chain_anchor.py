"""Decision chain verify + S3 anchor tests for Finance Governor sidecar."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
SIDECAR = ROOT / "spine" / "sidecar"
sys.path.insert(0, str(SIDECAR))

FG_TESTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(FG_TESTS))

from conftest_spine import spine_db  # noqa: F401

HEADERS = {"x-internal-token": "test-token"}


@pytest.fixture()
def client(spine_db):
    from app.main import app

    return TestClient(app)


def test_verify_chain_empty(client):
    r = client.get("/internal/decisions/verify-chain", headers=HEADERS)
    assert r.status_code == 200
    body = r.json()
    assert body["valid"] is True
    assert body["total_events"] == 0


def test_verify_chain_after_lifecycle(client):
    facets = {"amount": "10.00"}
    cr = client.post(
        "/crystallize",
        headers=HEADERS,
        json={"platform": "wire_match", "operation_id": "chain-1", "risk_tier": "low", "facets": facets},
    )
    crystal_id = cr.json()["crystal_id"]
    client.post(
        "/commit",
        headers=HEADERS,
        json={"crystal_id": crystal_id, "facets": facets, "committed_exposure": "0"},
    )
    verify = client.get("/internal/decisions/verify-chain", headers=HEADERS)
    assert verify.json()["valid"] is True
    assert verify.json()["head_hash"]


def test_anchor_head_s3_mock(client):
    facets = {"amount": "20.00"}
    cr = client.post(
        "/crystallize",
        headers=HEADERS,
        json={"platform": "wire_match", "operation_id": "anchor-1", "risk_tier": "low", "facets": facets},
    )
    crystal_id = cr.json()["crystal_id"]
    client.post(
        "/commit",
        headers=HEADERS,
        json={"crystal_id": crystal_id, "facets": facets, "committed_exposure": "0"},
    )

    from app.config import Settings, get_settings

    settings = Settings(
        database_url="sqlite+pysqlite:///:memory:",
        redis_url="redis://localhost:6380/0",
        fg_internal_tokens="test-token",
        ledger_anchor_s3_bucket="fg-audit-bucket",
        ledger_anchor_s3_object_lock_enabled=True,
    )
    mock_client = MagicMock()
    mock_boto3 = MagicMock()
    mock_boto3.client.return_value = mock_client
    with patch("app.decision_anchor_s3.get_settings", return_value=settings):
        with patch.dict(sys.modules, {"boto3": mock_boto3}):
            r = client.post("/internal/decisions/anchor-head", headers=HEADERS)
    assert r.status_code == 200
    assert r.json()["head_hash"]
    assert r.json().get("s3_anchored") is True
