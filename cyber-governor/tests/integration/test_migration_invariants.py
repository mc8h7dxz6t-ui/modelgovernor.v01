"""Cybersecurity Governor migration invariant tests."""
from __future__ import annotations

import os
from pathlib import Path

import pytest
from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[2]
MIGRATIONS = ROOT / "migrations"


def test_cyber_invariant_migrations_present() -> None:
    m3 = MIGRATIONS / "0003_invariant_constraints.sql"
    assert m3.exists()
    body = m3.read_text(encoding="utf-8")
    assert "cg_principal_nonnegative" in body
    assert "cg_action_reserved_within_cap" in body
    assert "cg_escrow_nonnegative_reserved" in body

    m2 = MIGRATIONS / "0002_security_anchors_lineage.sql"
    assert "security_chain_anchors" in m2.read_text(encoding="utf-8")
    assert "lineage_edges" in m2.read_text(encoding="utf-8")


@pytest.mark.skipif(
    not os.environ.get("CG_POSTGRES_TEST_URL") and not os.environ.get("POSTGRES_TEST_URL"),
    reason="Postgres URL not set",
)
def test_postgres_escrow_nonnegative_constraint(pg_engine):
    with pg_engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO threat_crystals (
                    crystal_id, platform, operation_id, risk_tier, facets,
                    request_fingerprint, crystal_hash, horizon_expires_at
                ) VALUES (
                    'tcrys_esc', 'identity_gate', 'op-esc', 'critical', '{}',
                    'fp', 'h1', NOW() + interval '1 hour'
                )
                """
            )
        )
        with pytest.raises(Exception):
            conn.execute(
                text(
                    """
                    INSERT INTO action_escrow_ledger (
                        operation_id, crystal_id, account_id, platform,
                        reserved_exposure, status, expires_at
                    ) VALUES (
                        'op-esc', 'tcrys_esc', 'tenant-default', 'identity_gate',
                        -1, 'CRYSTALLIZED', NOW() + interval '1 hour'
                    )
                    """
                )
            )
