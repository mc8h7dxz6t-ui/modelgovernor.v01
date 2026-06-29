"""CreditGovern platform tests."""
import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from platforms.credit_govern.main import app


@pytest.fixture()
def client():
    return TestClient(app)


def test_healthz(client):
    assert client.get("/healthz").json()["status"] == "ok"


def test_approved_model_approves_low_exposure(client, monkeypatch):
    monkeypatch.delenv("FG_SPINE_ENABLED", raising=False)
    r = client.post(
        "/credit/evaluate",
        json={
            "application_id": "app-1",
            "exposure_amount": "50000.00",
            "model_version_id": "credit-model-v3",
        },
    )
    assert r.status_code == 200
    assert r.json()["decision"] == "APPROVE"
    assert r.json()["crystal_id"] is None


def test_model_version_mismatch_blocked(client):
    r = client.post(
        "/credit/evaluate",
        json={
            "application_id": "app-2",
            "exposure_amount": "10000.00",
            "model_version_id": "credit-model-v99",
        },
    )
    assert r.json()["decision"] == "BLOCKED"
    assert r.json()["reason"] == "MODEL_VERSION_MISMATCH"


def test_high_exposure_refer(client, monkeypatch):
    monkeypatch.delenv("FG_SPINE_ENABLED", raising=False)
    r = client.post(
        "/credit/evaluate",
        json={
            "application_id": "app-3",
            "exposure_amount": "300000.00",
            "model_version_id": "credit-model-v4",
        },
    )
    assert r.json()["decision"] == "REFER"


def test_standalone_no_double_crystallize(client, monkeypatch):
    monkeypatch.setenv("FG_SPINE_ENABLED", "false")
    r = client.post(
        "/credit/evaluate",
        json={
            "application_id": "app-4",
            "exposure_amount": "25000.00",
            "model_version_id": "credit-model-v3",
        },
    )
    assert r.status_code == 200
    assert r.json()["crystal_id"] is None


def test_invalid_exposure_amount(client):
    r = client.post(
        "/credit/evaluate",
        json={
            "application_id": "app-5",
            "exposure_amount": "not-decimal",
            "model_version_id": "credit-model-v3",
        },
    )
    assert r.status_code == 422
