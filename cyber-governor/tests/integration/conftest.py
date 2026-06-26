"""Postgres fixtures for Cybersecurity Governor integration tests."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

ROOT = Path(__file__).resolve().parents[2]
SIDECAR = ROOT / "spine" / "sidecar"
sys.path.insert(0, str(SIDECAR))
sys.path.insert(0, str(ROOT))

from tests.helpers import apply_postgres_migrations, cg_settings

POSTGRES_URL = os.environ.get(
    "CG_POSTGRES_TEST_URL",
    os.environ.get("POSTGRES_TEST_URL", ""),
)


@pytest.fixture(scope="session")
def pg_engine() -> Engine:
    if not POSTGRES_URL:
        pytest.skip("CG_POSTGRES_TEST_URL not set")
    url = POSTGRES_URL
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    engine = create_engine(url, future=True, pool_pre_ping=True)
    apply_postgres_migrations(engine)
    yield engine
    engine.dispose()


@pytest.fixture()
def clean_cg_tables(pg_engine: Engine):
    tables = [
        "lineage_edges",
        "security_chain_anchors",
        "security_events",
        "guardrail_incidents",
        "platform_action_attempts",
        "action_escrow_ledger",
        "threat_crystals",
        "action_budget_state",
        "principal_budgets",
        "threat_mesh_rules",
        "control_policy_registry",
        "platform_registry",
    ]
    with pg_engine.begin() as conn:
        for table in tables:
            conn.execute(text(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE"))
        conn.execute(
            text(
                """
                INSERT INTO principal_budgets (account_id, ledger_type, currency, balance)
                VALUES ('tenant-default', 'action_budget', 'USD', 100000000)
                ON CONFLICT DO NOTHING
                """
            )
        )
        conn.execute(
            text(
                """
                INSERT INTO control_policy_registry (
                    policy_id, instrument_type, platform, jurisdiction, risk_classification,
                    max_exposure_per_commit, commit_horizon_ms, allow_auto_expire
                ) VALUES
                    ('identity-critical-us', 'session', 'identity_gate', 'US', 'critical',
                     1000000.000000000000, 30000, FALSE),
                    ('egress-critical-us', 'egress', 'egress_lock', 'US', 'critical',
                     1000000000.000000000000, 60000, FALSE),
                    ('witness-standard-us', 'telemetry', 'witness_bridge', 'US', 'standard',
                     100000.000000000000, 3600000, TRUE)
                ON CONFLICT (policy_id) DO NOTHING
                """
            )
        )
        conn.execute(
            text(
                """
                INSERT INTO threat_mesh_rules (parent_platform, parent_facet_key, parent_facet_value, child_platform)
                VALUES ('identity_gate', 'session_state', 'STRANDED', 'egress_lock')
                ON CONFLICT DO NOTHING
                """
            )
        )
    yield


@pytest.fixture()
def pg_settings(pg_engine):
    return cg_settings(str(pg_engine.url))
