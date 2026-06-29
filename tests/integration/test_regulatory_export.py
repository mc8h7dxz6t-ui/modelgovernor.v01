"""Regulatory export API — examiner bundle for ModelGovernor."""
from __future__ import annotations

from pathlib import Path
import sys

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from sidecar.app.ledger import reserve_operation
from sidecar.app.main import app
from sidecar.app.schemas import ReserveRequest
from tests.integration.test_ledger_hardening import _bootstrap_schema, _create_test_engine, _seed_wallet_and_model, _settings
from tests.integration.test_ledger_verify_chain import _configure

TOKEN = "test-token"
HEADERS = {"x-internal-token": TOKEN}


def test_regulatory_export_after_reserve(tmp_path, monkeypatch) -> None:
    engine = _configure(tmp_path, monkeypatch)
    settings = _settings(engine)

    with Session(engine) as session:
        reserve_operation(
            session,
            settings,
            ReserveRequest(
                user_id="user-1",
                trace_id="trace-reg",
                idempotency_key="reg-export-1",
                model="gpt-4o-mini",
                estimated_cost="1.000000",
            ),
        )
        session.commit()

    client = TestClient(app)
    response = client.get("/internal/regulatory/export", headers=HEADERS)
    assert response.status_code == 200
    body = response.json()
    assert body["chain_head"]
    assert len(body["ledger_events"]) >= 1
    assert "exported_at" in body
    assert "chain_verification" in body
    assert "diagnostic" in body
