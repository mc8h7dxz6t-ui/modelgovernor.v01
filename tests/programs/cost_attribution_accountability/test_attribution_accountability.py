"""AI Cost Attribution and Agent Accountability — institutional++ program test suite."""
from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from sidecar.app.config import Settings, get_settings
from sidecar.app.db import override_engine
from sidecar.app.ledger import PolicyStateError, TraceCapExceededError, reserve_operation
from sidecar.app.main import app
from sidecar.app.metrics import get_counters
from sidecar.app.schemas import ReserveRequest, SettleRequest
from tests.support.attribution_bootstrap import (
    bootstrap_attribution_schema,
    create_attribution_engine,
    seed_attribution_wallet,
)

TOKEN = "test-token"
HEADERS = {
    "x-internal-token": TOKEN,
    "x-tenant-id": "tenant-a",
    "x-session-id": "session-a",
    "x-agent-run-id": "run-a",
    "x-workflow-step": "step-plan",
}


def _settings(engine) -> Settings:
    return Settings(
        database_url=str(engine.url),
        redis_url="redis://example/0",
        sidecar_internal_tokens=TOKEN,
        default_trace_cap_amount=Decimal("1000"),
        default_run_budget_amount=Decimal("20"),
        default_session_budget_amount=Decimal("200"),
        default_user_budget_amount=Decimal("500"),
        default_tenant_budget_amount=Decimal("5000"),
        manual_approval_cost_threshold=Decimal("2"),
        max_loop_repeats=2,
        drift_absolute_tolerance=Decimal("100"),
        drift_ratio_tolerance=Decimal("1"),
        db_pool_size=4,
        db_max_overflow=4,
        db_pool_timeout_seconds=5,
        db_pool_recycle_seconds=1800,
    )


def test_attribution_budget_scope_enforced_per_agent_run(tmp_path: Path) -> None:
    engine = create_attribution_engine(tmp_path / "attr-scope.sqlite3")
    bootstrap_attribution_schema(engine)
    seed_attribution_wallet(engine)
    settings = _settings(engine)
    get_counters().reset()

    req = ReserveRequest(
        user_id="attr-user",
        trace_id="trace-1",
        idempotency_key="attr-op-1",
        model="gpt-4o-mini",
        estimated_cost=Decimal("15"),
        tenant_id="tenant-a",
        session_id="session-a",
        agent_run_id="run-a",
        workflow_step="step-plan",
        run_budget=Decimal("20"),
        manual_approval_id="approved-1",
    )
    with Session(engine) as session:
        reserve_operation(session, settings, req)

    with pytest.raises(TraceCapExceededError):
        with Session(engine) as session:
            reserve_operation(
                session,
                settings,
                ReserveRequest(
                    user_id="attr-user",
                    trace_id="trace-2",
                    idempotency_key="attr-op-2",
                    model="gpt-4o-mini",
                    estimated_cost=Decimal("10"),
                    tenant_id="tenant-a",
                    session_id="session-a",
                    agent_run_id="run-a",
                    workflow_step="step-plan",
                    run_budget=Decimal("20"),
                    manual_approval_id="approved-2",
                ),
            )

    assert get_counters().snapshot()["budget_scope_exceeded_total"] >= 1


def test_attribution_manual_approval_guardrail(tmp_path: Path) -> None:
    engine = create_attribution_engine(tmp_path / "attr-approval.sqlite3")
    bootstrap_attribution_schema(engine)
    seed_attribution_wallet(engine)
    settings = _settings(engine)
    get_counters().reset()

    with pytest.raises(PolicyStateError, match="manual approval"):
        with Session(engine) as session:
            reserve_operation(
                session,
                settings,
                ReserveRequest(
                    user_id="attr-user",
                    trace_id="trace-approval",
                    idempotency_key="approval-op",
                    model="gpt-4o-mini",
                    estimated_cost=Decimal("5"),
                    tenant_id="tenant-a",
                    session_id="session-a",
                    agent_run_id="run-a",
                    workflow_step="step-plan",
                ),
            )

    assert get_counters().snapshot()["guardrail_approval_required_total"] == 1


def test_attribution_summary_and_lineage_api(tmp_path: Path, monkeypatch) -> None:
    engine = create_attribution_engine(tmp_path / "attr-api.sqlite3")
    bootstrap_attribution_schema(engine)
    seed_attribution_wallet(engine)
    settings = _settings(engine)
    monkeypatch.setenv("DATABASE_URL", str(engine.url))
    monkeypatch.setenv("REDIS_URL", "redis://example/0")
    monkeypatch.setenv("SIDECAR_INTERNAL_TOKENS", TOKEN)
    get_settings.cache_clear()
    override_engine(engine)

    with Session(engine) as session:
        reserve_operation(
            session,
            settings,
            ReserveRequest(
                user_id="attr-user",
                trace_id="trace-api",
                idempotency_key="api-op",
                model="gpt-4o-mini",
                estimated_cost=Decimal("3"),
                tenant_id="tenant-a",
                session_id="session-a",
                agent_run_id="run-a",
                workflow_step="step-plan",
                manual_approval_id="approval-1",
            ),
        )
        from sidecar.app.ledger import apply_settlement

        apply_settlement(
            session,
            settings,
            SettleRequest(
                idempotency_key="api-op",
                outcome="SETTLED",
                actual_cost=Decimal("2.5"),
                input_tokens=100,
                output_tokens=50,
            ),
        )

    with TestClient(app) as client:
        summary = client.get("/internal/attribution/summary?dimension=tenant", headers=HEADERS)
        assert summary.status_code == 200
        payload = summary.json()
        assert payload["dimension"] == "tenant"
        assert any(row["group_key"] == "tenant-a" for row in payload["rows"])

        lineage = client.get("/internal/lineage/api-op", headers=HEADERS)
        assert lineage.status_code == 200
        records = lineage.json()["records"]
        assert len(records) >= 2
        assert {r["event_type"] for r in records} >= {"RESERVE_CREATED", "SETTLED_FINAL"}


def test_attribution_identity_mismatch_on_settle(tmp_path: Path) -> None:
    engine = create_attribution_engine(tmp_path / "attr-mismatch.sqlite3")
    bootstrap_attribution_schema(engine)
    seed_attribution_wallet(engine)
    settings = _settings(engine)
    get_counters().reset()

    with Session(engine) as session:
        reserve_operation(
            session,
            settings,
            ReserveRequest(
                user_id="attr-user",
                trace_id="trace-mis",
                idempotency_key="mis-op",
                model="gpt-4o-mini",
                estimated_cost=Decimal("2"),
                tenant_id="tenant-a",
                session_id="session-a",
                agent_run_id="run-a",
                workflow_step="step-plan",
                manual_approval_id="ok",
            ),
        )

    from sidecar.app.ledger import apply_settlement

    with pytest.raises(PolicyStateError):
        with Session(engine) as session:
            apply_settlement(
                session,
                settings,
                SettleRequest(
                    idempotency_key="mis-op",
                    outcome="SETTLED",
                    actual_cost=Decimal("2"),
                    tenant_id="tenant-b",
                ),
            )

    assert get_counters().snapshot()["attribution_identity_mismatch_total"] == 1
