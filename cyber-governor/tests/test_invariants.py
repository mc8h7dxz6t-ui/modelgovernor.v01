"""Threat ops and security ops invariant probes."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[1]
SIDECAR = ROOT / "spine" / "sidecar"
sys.path.insert(0, str(SIDECAR))

from tests.conftest_spine import spine_db  # noqa: F401


def test_security_ops_detects_negative_balance(spine_db):
    from app.security_ops import RegulatoryOpsInvariantError, assert_security_ops_invariants
    from app.db import get_db_session, override_engine

    override_engine(spine_db)
    with spine_db.begin() as conn:
        conn.execute(
            text(
                """
                UPDATE principal_budgets SET balance = -1
                WHERE account_id = 'tenant-default'
                """
            )
        )
    with get_db_session() as session:
        with pytest.raises(RegulatoryOpsInvariantError):
            assert_security_ops_invariants(session)


def test_threat_ops_clean_on_happy_path(spine_db):
    from app.threat_ops import assert_threat_ops_invariants
    from app.db import get_db_session, override_engine

    override_engine(spine_db)
    with get_db_session() as session:
        violations = assert_threat_ops_invariants(session)
        assert violations["committed_without_crystal"] == 0
