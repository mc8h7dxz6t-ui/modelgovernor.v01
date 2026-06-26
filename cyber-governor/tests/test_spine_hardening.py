"""Tier 1 — rigorous spine hardening (SQLite, institutional++ scenarios)."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[1]
SIDECAR = ROOT / "spine" / "sidecar"
sys.path.insert(0, str(SIDECAR))

from tests.helpers import cg_settings, create_sqlite_engine, identity_facets, session_factory


@pytest.fixture()
def engine(tmp_path):
    from app.db import override_engine

    eng = create_sqlite_engine(tmp_path / "hardening.sqlite3")
    override_engine(eng)
    yield eng
    override_engine(create_sqlite_engine(tmp_path / "discard.sqlite3"))


@pytest.fixture()
def settings(engine):
    return cg_settings(str(engine.url))


def test_crystallize_commit_happy_path_and_chain_valid(engine, settings):
    from app.commit_ledger import commit_operation, crystallize_operation
    from app.security_seal import verify_security_chain

    facets = identity_facets()
    Session = session_factory(engine)
    with Session() as s:
        cr = crystallize_operation(
            s, settings,
            platform="identity_gate",
            operation_id="hard-1",
            account_id="tenant-default",
            risk_tier="critical",
            facets=facets,
            policy_id="identity-critical-us",
        )
        crystal_id = cr.crystal_id
    with Session() as s:
        commit_operation(s, crystal_id=crystal_id, facets=facets, outcome="authorized")
    with Session() as s:
        result = verify_security_chain(s)
        assert result.valid is True
        assert result.sealed_count >= 2


def test_crystallize_idempotent_replay(engine, settings):
    from app.commit_ledger import crystallize_operation

    facets = identity_facets()
    Session = session_factory(engine)
    with Session() as s:
        a = crystallize_operation(
            s, settings, platform="identity_gate", operation_id="hard-replay",
            account_id="tenant-default", risk_tier="critical", facets=facets,
        )
    with Session() as s:
        b = crystallize_operation(
            s, settings, platform="identity_gate", operation_id="hard-replay",
            account_id="tenant-default", risk_tier="critical", facets=facets,
        )
    assert a.crystal_id == b.crystal_id
    assert b.status == "REPLAY"


def test_commit_fingerprint_mismatch_blocked(engine, settings):
    from app.commit_ledger import (
        HorizonStrandedError,
        SurpriseCommitBlockedError,
        commit_operation,
        crystallize_operation,
    )

    facets = identity_facets()
    Session = session_factory(engine)
    with Session() as s:
        cr = crystallize_operation(
            s, settings, platform="identity_gate", operation_id="hard-fp",
            account_id="tenant-default", risk_tier="critical", facets=facets,
        )
        crystal_id = cr.crystal_id
    with Session() as s:
        with pytest.raises(SurpriseCommitBlockedError):
            commit_operation(
                s, crystal_id=crystal_id,
                facets=identity_facets(session_state="STRANDED"),
            )


def test_horizon_expired_strands_critical_commit(engine, settings):
    from app.commit_ledger import HorizonStrandedError, commit_operation, crystallize_operation
    from platforms.common.threat_crystal import seal_crystal

    facets = identity_facets()
    crystal = seal_crystal(
        platform="identity_gate", operation_id="hard-expired",
        risk_tier="critical", facets=facets, horizon_ms=1,
    )
    past = (datetime.now(timezone.utc) - timedelta(seconds=10)).isoformat()
    Session = session_factory(engine)
    with Session() as s:
        s.execute(
            text(
                """
                INSERT INTO threat_crystals (
                    crystal_id, platform, operation_id, risk_tier, facets,
                    request_fingerprint, crystal_hash, horizon_expires_at
                ) VALUES (
                    :cid, :plat, :op, 'critical', :facets, :fp, :ch, :horizon
                )
                """
            ),
            {
                "cid": crystal.crystal_id,
                "plat": "identity_gate",
                "op": "hard-expired",
                "facets": json.dumps(facets),
                "fp": crystal.request_fingerprint,
                "ch": crystal.crystal_hash,
                "horizon": past,
            },
        )
        s.execute(
            text(
                """
                INSERT INTO action_escrow_ledger (
                    operation_id, crystal_id, account_id, platform,
                    reserved_exposure, status, expires_at
                ) VALUES (
                    'hard-expired', :cid, 'tenant-default', 'identity_gate',
                    0, 'CRYSTALLIZED', :horizon
                )
                """
            ),
            {"cid": crystal.crystal_id, "horizon": past},
        )
        s.commit()
    with Session() as s:
        with pytest.raises(HorizonStrandedError):
            commit_operation(s, crystal_id=crystal.crystal_id, facets=facets)


def test_mesh_blocks_egress_when_identity_stranded(engine, settings):
    from app.commit_ledger import SurpriseCommitBlockedError, commit_operation, crystallize_operation

    Session = session_factory(engine)
    with Session() as s:
        s.execute(
            text(
                """
                INSERT INTO threat_crystals (
                    crystal_id, platform, operation_id, risk_tier, facets,
                    request_fingerprint, crystal_hash, horizon_expires_at
                ) VALUES (
                    'tcrys_mesh', 'identity_gate', 'sess-mesh', 'critical',
                    :facets, 'fp', 'h1', datetime('now', '+1 hour')
                )
                """
            ),
            {"facets": json.dumps({"session_state": "STRANDED"})},
        )
        s.commit()
    egress = {"destination": "s3://corp", "byte_count": 100}
    with Session() as s:
        cr = crystallize_operation(
            s, settings, platform="egress_lock", operation_id="eg-mesh",
            account_id="tenant-default", risk_tier="critical", facets=egress,
        )
    with Session() as s:
        with pytest.raises(SurpriseCommitBlockedError):
            commit_operation(s, crystal_id=cr.crystal_id, facets=egress, outcome="allowed")


def test_insufficient_action_budget_blocks_crystallize(engine, settings):
    from app.commit_ledger import InsufficientExposureError, crystallize_operation

    Session = session_factory(engine)
    with Session() as s:
        s.execute(
            text(
                """
                UPDATE principal_budgets SET balance = 0
                WHERE account_id = 'tenant-default'
                """
            )
        )
        s.commit()
    with Session() as s:
        with pytest.raises(InsufficientExposureError):
            crystallize_operation(
                s, settings, platform="egress_lock", operation_id="hard-budget",
                account_id="tenant-default", risk_tier="critical",
                facets={"byte_count": 100}, reserved_exposure=Decimal("1000"),
            )


def test_horizon_sweep_preserves_chain(engine, settings):
    from app.horizon_sweep import sweep_expired_horizons
    from app.security_seal import verify_security_chain

    Session = session_factory(engine)
    with Session() as s:
        s.execute(
            text(
                """
                INSERT INTO threat_crystals (
                    crystal_id, platform, operation_id, risk_tier, facets,
                    request_fingerprint, crystal_hash, horizon_expires_at
                ) VALUES (
                    'tcrys_sweep', 'identity_gate', 'op-sweep', 'critical', '{}',
                    'fp', 'h1', datetime('now', '-1 hour')
                )
                """
            )
        )
        s.execute(
            text(
                """
                INSERT INTO action_escrow_ledger (
                    operation_id, crystal_id, account_id, platform,
                    reserved_exposure, status, expires_at
                ) VALUES (
                    'op-sweep', 'tcrys_sweep', 'tenant-default', 'identity_gate',
                    0, 'CRYSTALLIZED', datetime('now', '-1 hour')
                )
                """
            )
        )
        s.commit()
    with Session() as s:
        assert sweep_expired_horizons(s) == 1
        result = verify_security_chain(s)
        assert result.valid is True


def test_anchor_head_records_on_valid_chain(engine, settings):
    from app.commit_ledger import commit_operation, crystallize_operation
    from app.security_anchor import anchor_verified_security_chain_head

    facets = identity_facets()
    Session = session_factory(engine)
    with Session() as s:
        cr = crystallize_operation(
            s, settings, platform="identity_gate", operation_id="hard-anchor",
            account_id="tenant-default", risk_tier="critical", facets=facets,
        )
        crystal_id = cr.crystal_id
    with Session() as s:
        commit_operation(s, crystal_id=crystal_id, facets=facets, outcome="authorized")
    with Session() as s:
        payload = anchor_verified_security_chain_head(s, source="test")
        assert payload["anchored"] is True
        assert payload["head_hash"] is not None
