"""Incremental chain verification at scale — O(delta) checkpoint semantics."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

ROOT = Path(__file__).resolve().parents[1]
SIDECAR = ROOT / "spine" / "sidecar"
sys.path.insert(0, str(SIDECAR))

from tests.conftest_spine import spine_db  # noqa: F401
from support.cyber_fixtures import EGRESS_PLATFORM, EGRESS_POLICY, egress_facets


CHECKPOINT_DDL = """
CREATE TABLE security_chain_verify_checkpoints (
    checkpoint_id INTEGER PRIMARY KEY AUTOINCREMENT,
    singleton_key INTEGER NOT NULL DEFAULT 1 UNIQUE,
    last_verified_event_id INTEGER NOT NULL,
    verified_head_hash VARCHAR(64) NOT NULL,
    sealed_count INTEGER NOT NULL,
    total_events INTEGER NOT NULL,
    verified_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


def _crystallize_pair(session, settings, op_suffix: str) -> None:
    from decimal import Decimal

    from app.commit_ledger import crystallize_operation

    facets = egress_facets(flow_id=f"inc-{op_suffix}")
    crystallize_operation(
        session,
        settings,
        platform=EGRESS_PLATFORM,
        operation_id=f"inc-{op_suffix}",
        account_id="tenant-default",
        risk_tier="high",
        facets=facets,
        policy_id=EGRESS_POLICY,
        reserved_budget=Decimal("0"),
    )


def test_incremental_verify_uses_checkpoint_on_unchanged_head(spine_db):
    from app.config import get_settings
    from app.db import get_db_session
    from app.security_seal import verify_security_chain

    with spine_db.begin() as conn:
        conn.execute(text(CHECKPOINT_DDL))

    settings = get_settings()
    factory = sessionmaker(bind=spine_db)
    with factory() as session:
        _crystallize_pair(session, settings, "a")
        session.commit()

    with factory() as session:
        first = verify_security_chain(session, incremental=True)
        assert first.valid is True
        assert first.incremental is False
        assert first.total_events >= 1

    with factory() as session:
        second = verify_security_chain(session, incremental=True)
        assert second.valid is True
        assert second.incremental is True
        assert second.sealed_count == first.sealed_count
        assert second.head_hash == first.head_hash


def test_incremental_verify_tail_after_new_events(spine_db):
    from app.config import get_settings
    from app.db import get_db_session
    from app.security_seal import verify_security_chain

    with spine_db.begin() as conn:
        conn.execute(text(CHECKPOINT_DDL))

    settings = get_settings()
    factory = sessionmaker(bind=spine_db)
    with factory() as session:
        _crystallize_pair(session, settings, "base")
        session.commit()
        baseline = verify_security_chain(session, incremental=True)
        assert baseline.valid is True

    with factory() as session:
        _crystallize_pair(session, settings, "tail")
        session.commit()
        updated = verify_security_chain(session, incremental=True)
        assert updated.valid is True
        assert updated.total_events > baseline.total_events
        assert updated.sealed_count > baseline.sealed_count

    with factory() as session:
        cached = verify_security_chain(session, incremental=True)
        assert cached.incremental is True
        assert cached.sealed_count == updated.sealed_count
