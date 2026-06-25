"""Credit decision governance program tests."""
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from platforms.credit_govern.credit_schema import CreditRequest
from platforms.credit_govern.mock_rail import score_application
from platforms.credit_govern.main import app
from decimal import Decimal


@pytest.fixture()
def client():
    return TestClient(app)


def test_credit_request_schema_validates_decimal():
    req = CreditRequest(
        application_id="a1",
        exposure_amount="1000.00",
        model_version_id="credit-model-v3",
    )
    assert req.exposure_amount == "1000.00"


def test_mock_rail_approve_under_cap():
    outcome = score_application(exposure=Decimal("100000"), model_version_id="credit-model-v3")
    assert outcome.decision == "APPROVE"
    assert outcome.explanation_id


def test_reserve_before_score_flow(client, monkeypatch):
    monkeypatch.setenv("FG_SPINE_ENABLED", "false")
    r = client.post(
        "/credit/evaluate",
        json={
            "application_id": "prog-app-1",
            "exposure_amount": "75000.00",
            "model_version_id": "credit-model-v4",
            "desk_id": "desk-default",
            "feature_snapshot_hash": "abc123",
        },
    )
    body = r.json()
    assert body["decision"] in {"APPROVE", "REFER", "BLOCKED"}
    assert body["explanation_id"]
