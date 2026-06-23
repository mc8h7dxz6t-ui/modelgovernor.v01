"""SQLite bootstrap including attribution and accountability schema."""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.engine import Engine

from tests.integration.test_ledger_hardening import _bootstrap_schema, _create_test_engine, _seed_wallet_and_model

__all__ = ["bootstrap_attribution_schema", "create_attribution_engine", "seed_attribution_wallet"]


def create_attribution_engine(path) -> Engine:
    return _create_test_engine(path)


def seed_attribution_wallet(engine: Engine, *, user_id: str = "attr-user", balance=1000) -> None:
    _seed_wallet_and_model(engine, user_id=user_id, balance=balance)


def bootstrap_attribution_schema(engine: Engine) -> None:
    _bootstrap_schema(engine)
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS budget_scope_state (
                    scope_type TEXT NOT NULL,
                    scope_key TEXT NOT NULL,
                    cap_amount NUMERIC(18,6) NOT NULL,
                    consumed_amount NUMERIC(18,6) NOT NULL DEFAULT 0,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (scope_type, scope_key)
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS guardrail_incidents (
                    incident_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    idempotency_key TEXT,
                    user_id TEXT,
                    tenant_id TEXT,
                    session_id TEXT,
                    agent_run_id TEXT,
                    workflow_step TEXT,
                    incident_type TEXT NOT NULL,
                    details TEXT NOT NULL DEFAULT '{}',
                    recorded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS execution_loop_state (
                    scope_key TEXT PRIMARY KEY,
                    last_signature TEXT NOT NULL,
                    consecutive_count INTEGER NOT NULL DEFAULT 1,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS execution_lineage (
                    lineage_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    idempotency_key TEXT NOT NULL,
                    tenant_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    agent_run_id TEXT NOT NULL,
                    workflow_step TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    prompt_template_version TEXT,
                    system_context_hash TEXT,
                    tool_name TEXT,
                    tool_input TEXT,
                    raw_tool_output TEXT,
                    provider_request_id TEXT,
                    state_snapshot TEXT NOT NULL DEFAULT '{}',
                    recorded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        )
        for col, typedef in (
            ("tenant_id", "TEXT NOT NULL DEFAULT 'default-tenant'"),
            ("session_id", "TEXT NOT NULL DEFAULT 'default-session'"),
            ("agent_run_id", "TEXT NOT NULL DEFAULT 'default-agent-run'"),
            ("workflow_step", "TEXT NOT NULL DEFAULT 'default-workflow-step'"),
            ("policy_version", "TEXT NOT NULL DEFAULT 'v1'"),
            ("input_tokens", "INTEGER NOT NULL DEFAULT 0"),
            ("output_tokens", "INTEGER NOT NULL DEFAULT 0"),
            ("cached_input_tokens", "INTEGER NOT NULL DEFAULT 0"),
            ("cached_output_tokens", "INTEGER NOT NULL DEFAULT 0"),
            ("latency_ms", "INTEGER NOT NULL DEFAULT 0"),
            ("retry_count", "INTEGER NOT NULL DEFAULT 0"),
            ("failover_count", "INTEGER NOT NULL DEFAULT 0"),
            ("prompt_template_version", "TEXT"),
            ("system_context_hash", "TEXT"),
            ("tool_name", "TEXT"),
            ("raw_tool_output", "TEXT"),
        ):
            try:
                conn.execute(text(f"ALTER TABLE escrow_ledger ADD COLUMN {col} {typedef}"))
            except Exception:
                pass
