"""WireMatch platform tests."""
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from platforms.wire_match.main import app


@pytest.fixture()
def client():
    return TestClient(app)


def test_valid_wire_approved(client):
    r = client.post(
        "/wire/evaluate",
        json={
            "wire_id": "w1",
            "beneficiary_name": "Revlon Lenders Group",
            "beneficiary_account": "US12REV001",
            "reference": "loan payment",
            "amount": "7800000.00",
        },
    )
    assert r.status_code == 200
    assert r.json()["decision"] == "APPROVED"


def test_amount_anomaly_held(client):
    r = client.post(
        "/wire/evaluate",
        json={
            "wire_id": "w2",
            "beneficiary_name": "Revlon Lenders Group",
            "beneficiary_account": "US12REV001",
            "reference": "loan payment",
            "amount": "900000000.00",
        },
    )
    assert r.json()["decision"] == "HELD"
    assert r.json()["reason"] == "AMOUNT_ANOMALY"


def test_beneficiary_mismatch_held(client):
    r = client.post(
        "/wire/evaluate",
        json={
            "wire_id": "w3",
            "beneficiary_name": "Totally Wrong Corp",
            "beneficiary_account": "US99WRONG",
            "reference": "payment",
            "amount": "7800000.00",
        },
    )
    assert r.json()["decision"] == "HELD"
    assert r.json()["reason"] == "BENEFICIARY_MISMATCH"


def test_decimal_type_rejects_float_string(client):
    r = client.post(
        "/wire/evaluate",
        json={
            "wire_id": "w4",
            "beneficiary_name": "Revlon Lenders Group",
            "beneficiary_account": "US12REV001",
            "reference": "x",
            "amount": "not-a-decimal",
        },
    )
    assert r.status_code == 422


def test_iso20022_evaluate(client):
    msg = (
        "<EndToEndId>iso-1</EndToEndId>"
        "<Nm>Revlon Lenders Group</Nm>"
        "<IBAN>US12REV001</IBAN>"
        "<InstdAmt>7800000.00</InstdAmt>"
        "<Ccy>USD</Ccy>"
    )
    r = client.post("/wire/evaluate-iso20022", json={"message": msg})
    assert r.json()["decision"] == "APPROVED"


def test_wire_send_idempotency(client):
    body = {
        "wire_id": "send-1",
        "beneficiary_name": "Revlon Lenders Group",
        "beneficiary_account": "US12REV001",
        "amount": "7800000.00",
        "idempotency_key": "idem-1",
    }
    first = client.post("/wire/send", json=body)
    assert first.json()["status"] == "SENT"
    second = client.post("/wire/send", json=body)
    assert second.json()["status"] == "DUPLICATE"
