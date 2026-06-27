"""Incremental claim chain verification — O(delta) checkpoint semantics."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

ROOT = Path(__file__).resolve().parents[1]
SIDECAR = ROOT / "spine" / "sidecar"
sys.path.insert(0, str(SIDECAR))

from tests.conftest_spine import spine_db  # noqa: F401

HEADERS = {"x-internal-token": "test-token"}

CHECKPOINT_DDL = """
CREATE TABLE claim_chain_verify_checkpoints (
    checkpoint_id INTEGER PRIMARY KEY AUTOINCREMENT,
    singleton_key INTEGER NOT NULL DEFAULT 1 UNIQUE,
    last_verified_event_id INTEGER NOT NULL,
    verified_head_hash VARCHAR(64) NOT NULL,
    sealed_count INTEGER NOT NULL,
    total_events INTEGER NOT NULL,
    verified_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


def _crystallize(client: TestClient, op_id: str) -> None:
    facets = {"claim_id": op_id, "payout_amount": "50.00"}
    client.post(
        "/crystallize",
        headers=HEADERS,
        json={
            "platform": "claim_gate",
            "operation_id": op_id,
            "risk_tier": "standard",
            "facets": facets,
        },
    )


def test_incremental_verify_uses_checkpoint_on_unchanged_head(spine_db):
    from app.claim_seal import verify_claim_chain

    with spine_db.begin() as conn:
        conn.execute(text(CHECKPOINT_DDL))

    client = TestClient(__import__("app.main", fromlist=["app"]).app)
    _crystallize(client, "inc-a")

    factory = sessionmaker(bind=spine_db)
    with factory() as session:
        first = verify_claim_chain(session, incremental=True)
        assert first.valid is True
        assert first.incremental is False

    with factory() as session:
        second = verify_claim_chain(session, incremental=True)
        assert second.valid is True
        assert second.incremental is True


def test_incremental_verify_tail_after_new_events(spine_db):
    from app.claim_seal import verify_claim_chain

    with spine_db.begin() as conn:
        conn.execute(text(CHECKPOINT_DDL))

    client = TestClient(__import__("app.main", fromlist=["app"]).app)
    _crystallize(client, "inc-base")

    factory = sessionmaker(bind=spine_db)
    with factory() as session:
        baseline = verify_claim_chain(session, incremental=True)
        assert baseline.valid is True

    _crystallize(client, "inc-tail")
    with factory() as session:
        updated = verify_claim_chain(session, incremental=True)
        assert updated.valid is True
        assert updated.total_events > baseline.total_events
