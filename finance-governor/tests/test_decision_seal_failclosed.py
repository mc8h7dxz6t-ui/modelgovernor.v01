"""Decision chain verification — fail-closed semantics."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[1]
SIDECAR = ROOT / "spine" / "sidecar"
sys.path.insert(0, str(SIDECAR))

from tests.conftest_spine import spine_db  # noqa: F401


def test_verify_chain_fails_without_seal_columns(spine_db):
    from app.decision_seal import verify_decision_chain
    from sqlalchemy.orm import sessionmaker

    with spine_db.begin() as conn:
        conn.execute(text("ALTER TABLE decision_events DROP COLUMN row_hash"))

    factory = sessionmaker(bind=spine_db)
    with factory() as session:
        result = verify_decision_chain(session)
        assert result.valid is False
        assert result.first_break is not None
        assert result.first_break.reason == "seal_schema_unavailable"
