"""Horizon sweeper preserves hash chain integrity."""
from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[1]
SIDECAR = ROOT / "spine" / "sidecar"
sys.path.insert(0, str(SIDECAR))

from tests.conftest_spine import spine_db  # noqa: F401


def test_horizon_sweep_strands_and_preserves_chain(spine_db):
    from app.db import get_db_session, override_engine
    from app.security_seal import verify_security_chain
    from app.horizon_sweep import sweep_expired_horizons

    override_engine(spine_db)
    with spine_db.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO threat_crystals (
                    crystal_id, platform, operation_id, risk_tier, facets,
                    request_fingerprint, crystal_hash, horizon_expires_at
                ) VALUES (
                    'tcrys_expired', 'identity_gate', 'op-exp', 'critical', '{}',
                    'fp', 'h1', datetime('now', '-1 hour')
                )
                """
            )
        )
        conn.execute(
            text(
                """
                INSERT INTO action_escrow_ledger (
                    operation_id, crystal_id, account_id, platform,
                    reserved_exposure, status, expires_at
                ) VALUES (
                    'op-exp', 'tcrys_expired', 'tenant-default', 'identity_gate',
                    0, 'CRYSTALLIZED', datetime('now', '-1 hour')
                )
                """
            )
        )

    with get_db_session() as session:
        swept = sweep_expired_horizons(session)
        assert swept == 1
        result = verify_security_chain(session)
        assert result.valid is True
        assert result.sealed_count >= 1
