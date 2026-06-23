from __future__ import annotations

import sqlite3
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from sidecar.app.config import Settings
from sidecar.app.orchestration import OrchestrationPolicyError, run_orchestration_workflow
from sidecar.app.schemas import ComputationTask, OrchestrationWorkflowRequest, SourceDocument

sqlite3.register_adapter(Decimal, lambda v: str(v))


def _settings() -> Settings:
    return Settings(
        database_url="sqlite:///:memory:",
        redis_url="redis://localhost:6379/0",
        sidecar_internal_tokens="token",
        orchestration_runtime_mode="coexisting",
        orchestration_shadow_mode=True,
        orchestration_cache_ttl_seconds=900,
    )


def _build_engine(tmp_path: Path) -> Engine:
    engine = create_engine(
        f"sqlite:///{tmp_path / 'orchestration-plane.db'}",
        connect_args={"check_same_thread": False},
        future=True,
    )
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE orchestration_audit_log (
                    audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL,
                    workflow_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    runtime_mode TEXT NOT NULL,
                    state TEXT NOT NULL,
                    agent TEXT NOT NULL,
                    status TEXT NOT NULL,
                    details TEXT NOT NULL DEFAULT '{}',
                    recorded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE orchestration_semantic_cache (
                    cache_key TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL,
                    response_json TEXT NOT NULL,
                    expires_at TIMESTAMP NOT NULL,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        )
    return engine


def test_standalone_orchestration_runs_with_critic_and_deterministic_compute(tmp_path: Path) -> None:
    engine = _build_engine(tmp_path)
    settings = _settings()

    request = OrchestrationWorkflowRequest(
        workflow_id="wf-001",
        user_id="ops-user",
        runtime_mode="standalone",
        query="calculate projected spend",
        regulated=True,
        documents=[
            SourceDocument(
                document_id="doc-1",
                source_uri="file://policy-a.md",
                content="Projected monthly spend baseline is 120.00 and growth factor is 1.10.",
            )
        ],
        computations=[
            ComputationTask(
                task_id="growth",
                expression="baseline * factor",
                variables={"baseline": Decimal("120.00"), "factor": Decimal("1.10")},
                expected_unit="USD",
            )
        ],
    )

    with Session(engine) as session:
        response = run_orchestration_workflow(session, settings, request)

    assert response.state == "PUBLISHED"
    assert response.critic_passed is True
    assert response.computations[0].value == Decimal("132.000000")
    assert response.citations
    assert "deterministic_compute_sandbox" in response.tech_edges
    assert response.agent_decisions[-1].agent == "critic"


def test_coexisting_mode_requires_external_context_id(tmp_path: Path) -> None:
    engine = _build_engine(tmp_path)
    settings = _settings()
    request = OrchestrationWorkflowRequest(
        workflow_id="wf-002",
        user_id="ops-user",
        runtime_mode="coexisting",
        query="prepare summary",
        documents=[],
    )

    with Session(engine) as session:
        with pytest.raises(OrchestrationPolicyError, match="external_context_id is required"):
            run_orchestration_workflow(session, settings, request)


def test_semantic_cache_short_circuits_repeat_workflows(tmp_path: Path) -> None:
    engine = _build_engine(tmp_path)
    settings = _settings()
    request = OrchestrationWorkflowRequest(
        workflow_id="wf-003",
        user_id="ops-user",
        runtime_mode="standalone",
        query="summarize cap policy",
        documents=[
            SourceDocument(
                document_id="doc-2",
                source_uri="file://policy-b.md",
                content="Trace cap policy requires reserve-before-dispatch and deterministic audit trails.",
            )
        ],
    )

    with Session(engine) as session:
        first = run_orchestration_workflow(session, settings, request)

    with Session(engine) as session:
        second = run_orchestration_workflow(session, settings, request)

    assert first.cache_hit is False
    assert second.cache_hit is True
    assert second.run_id == first.run_id
