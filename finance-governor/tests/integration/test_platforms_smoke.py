"""All Finance Governor platforms — health and core API smoke."""
from __future__ import annotations

import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def test_all_fg_platforms_health_and_core_apis():
    from platforms.algofreeze.main import app as algo_app
    from platforms.credit_govern.main import app as credit_app
    from platforms.subledger_sync.main import app as subledger_app
    from platforms.wire_match.main import app as wire_app

    wire = TestClient(wire_app)
    assert wire.get("/healthz").status_code == 200
    held = wire.post(
        "/wire/evaluate",
        json={
            "wire_id": "smoke-1",
            "beneficiary_name": "Revlon Lenders Group",
            "beneficiary_account": "US12REV001",
            "reference": "payment",
            "amount": "900000000.00",
        },
    )
    assert held.json()["decision"] == "HELD"

    algo = TestClient(algo_app)
    assert algo.get("/healthz").status_code == 200

    subledger = TestClient(subledger_app)
    assert subledger.get("/healthz").status_code == 200
    subledger.post(
        "/transactions",
        json={
            "entity_id": "UK-01",
            "counterparty_id": "US-01",
            "amount": "10000.00",
            "currency": "USD",
            "value_date": "2026-06-01",
        },
    )
    matched = subledger.post(
        "/match/run",
        json={
            "entity_id": "US-01",
            "counterparty_id": "UK-01",
            "amount": "10000.00",
            "currency": "USD",
            "value_date": "2026-06-01",
        },
    )
    assert matched.json()["status"] == "MATCHED"
    assert matched.json()["fx_hash"]

    credit = TestClient(credit_app)
    assert credit.get("/healthz").status_code == 200
    approved = credit.post(
        "/credit/evaluate",
        json={
            "application_id": "smoke-credit-1",
            "exposure_amount": "50000.00",
            "model_version_id": "credit-model-v3",
            "desk_id": "desk-default",
        },
    )
    assert approved.json()["decision"] == "APPROVE"
    blocked = credit.post(
        "/credit/evaluate",
        json={
            "application_id": "smoke-credit-2",
            "exposure_amount": "10000.00",
            "model_version_id": "credit-model-v99",
        },
    )
    assert blocked.json()["decision"] == "BLOCKED"
