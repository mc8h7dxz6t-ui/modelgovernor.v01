"""Shared test helpers for Cybersecurity Governor spine."""
from __future__ import annotations

import sys
from decimal import Decimal
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

ROOT = Path(__file__).resolve().parents[1]
SIDECAR = ROOT / "spine" / "sidecar"
if str(SIDECAR) not in sys.path:
    sys.path.insert(0, str(SIDECAR))

SCHEMA_SQLITE = (ROOT / "tests" / "schema_sqlite.sql").read_text(encoding="utf-8")
MIGRATIONS_DIR = ROOT / "migrations"


def cg_settings(database_url: str, **overrides):
    from app.config import Settings

    defaults = {
        "database_url": database_url,
        "redis_url": "redis://localhost:6390/0",
        "cg_internal_tokens": "test-token",
        "commit_ttl_seconds": 300,
    }
    defaults.update(overrides)
    return Settings(**defaults)


def apply_sqlite_schema(engine: Engine) -> None:
    with engine.begin() as conn:
        for stmt in SCHEMA_SQLITE.split(";"):
            s = stmt.strip()
            if s:
                conn.execute(text(s))


def apply_postgres_migrations(engine: Engine) -> None:
    with engine.begin() as conn:
        for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
            sql = path.read_text(encoding="utf-8")
            conn.execute(text(sql))


def create_sqlite_engine(path: Path) -> Engine:
    engine = create_engine(
        f"sqlite+pysqlite:///{path}",
        connect_args={"check_same_thread": False},
        future=True,
    )
    apply_sqlite_schema(engine)
    return engine


def session_factory(engine: Engine):
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def identity_facets(**extra) -> dict:
    base = {
        "user_id": "alice@corp.example",
        "device_fingerprint": "dev_fp_trusted",
        "session_state": "AUTHORIZED",
    }
    base.update(extra)
    return base


CG_TRUNCATE_TABLES = [
    "admin_audit_log",
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


def truncate_cg_tables(conn) -> None:
    for table in CG_TRUNCATE_TABLES:
        conn.execute(text(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE"))


def reseed_cg_bootstrap(conn) -> None:
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


def reset_cg_tables(engine: Engine) -> None:
    with engine.begin() as conn:
        truncate_cg_tables(conn)
        reseed_cg_bootstrap(conn)

