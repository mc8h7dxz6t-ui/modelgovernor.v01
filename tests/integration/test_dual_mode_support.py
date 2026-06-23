from __future__ import annotations

from decimal import Decimal
from pathlib import Path
import sys

from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from sidecar.app.config import get_settings
from sidecar.app.db import override_engine
from sidecar.app.ledger import OperationResult
from sidecar.app.main import app
from sidecar.app import routes_reserve, routes_settle
from tests.integration.test_ledger_hardening import _create_test_engine

TOKEN = "test-token"
HEADERS = {
    "x-internal-token": TOKEN,
    "x-tenant-id": "tenant-1",
    "x-session-id": "session-1",
    "x-agent-run-id": "run-1",
    "x-workflow-step": "step-1",
}


def test_standalone_direct_sidecar_reserve_and_settle_contract(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "dual_mode.sqlite3"
    engine = _create_test_engine(db_path)
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("REDIS_URL", "redis://example/0")
    monkeypatch.setenv("SIDECAR_INTERNAL_TOKENS", TOKEN)
    get_settings.cache_clear()
    override_engine(engine)

    def _fake_reserve(_session, _settings, request):
        assert request.tenant_id == "tenant-1"
        assert request.session_id == "session-1"
        assert request.agent_run_id == "run-1"
        assert request.workflow_step == "step-1"
        return OperationResult(
            idempotency_key=request.idempotency_key,
            status="RESERVED",
            actual_amount=Decimal("0.000000"),
        )

    def _fake_settle(_session, _settings, request):
        assert request.tenant_id == "tenant-1"
        assert request.session_id == "session-1"
        assert request.agent_run_id == "run-1"
        assert request.workflow_step == "step-1"
        return OperationResult(
            idempotency_key=request.idempotency_key or "op-standalone-1",
            status="SETTLED",
            actual_amount=Decimal("0.900000"),
        )

    monkeypatch.setattr(routes_reserve, "reserve_operation", _fake_reserve)
    monkeypatch.setattr(routes_settle, "apply_settlement", _fake_settle)

    with TestClient(app) as client:
        reserve = client.post(
            "/reserve",
            headers=HEADERS,
            json={
                "user_id": "user-1",
                "trace_id": "trace-standalone-1",
                "idempotency_key": "op-standalone-1",
                "model": "gpt-4o-mini",
                "estimated_cost": "1.000000",
            },
        )
        assert reserve.status_code == 200
        assert reserve.json()["status"] == "RESERVED"

        settle = client.post(
            "/settle",
            headers=HEADERS,
            json={
                "idempotency_key": "op-standalone-1",
                "outcome": "SETTLED",
                "actual_cost": "0.900000",
            },
        )
        assert settle.status_code == 200
        settle_payload = settle.json()
        assert settle_payload["idempotency_key"] == "op-standalone-1"
        assert settle_payload["status"] == "SETTLED"
        assert Decimal(settle_payload["actual_amount"]) == Decimal("0.900000")


def test_governed_mode_gateway_contract_artifacts_present() -> None:
    gateway_config = (
        REPO_ROOT / "gateway" / "litellm.config.yaml"
    ).read_text(encoding="utf-8")
    assert "model_list:" in gateway_config
    assert "master_key: os.environ/LITELLM_MASTER_KEY" in gateway_config
    assert "openai/gpt-4o-mini" in gateway_config
