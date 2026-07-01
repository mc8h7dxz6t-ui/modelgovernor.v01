"""H1 — concurrent decision append stays chain-valid under Postgres advisory lock."""
from __future__ import annotations

import sys
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

ROOT = Path(__file__).resolve().parents[2]
SIDECAR = ROOT / "spine" / "sidecar"
if str(SIDECAR) not in sys.path:
    sys.path.insert(0, str(SIDECAR))

spine_core_root = ROOT.parent / "governor-spine-core"
if str(spine_core_root) not in sys.path:
    sys.path.insert(0, str(spine_core_root))


@pytest.fixture()
def clean_decision_events(postgres_engine):
    with postgres_engine.begin() as conn:
        conn.execute(text("TRUNCATE decision_events RESTART IDENTITY CASCADE"))
        conn.execute(text("TRUNCATE decision_chain_verify_checkpoints RESTART IDENTITY CASCADE"))


def test_concurrent_decision_append_chain_stays_valid(postgres_engine, clean_decision_events) -> None:
    from app.decision_seal import append_decision_event, verify_decision_chain

    factory = sessionmaker(bind=postgres_engine)

    def append_one(op_suffix: str) -> None:
        with factory() as session:
            append_decision_event(
                session,
                operation_id=f"conc-{op_suffix}",
                crystal_id=None,
                account_id="treasury-default",
                event_type="RESERVED",
                exposure_delta=Decimal("1.00"),
                metadata={"probe": op_suffix},
            )
            session.commit()

    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(append_one, [str(i) for i in range(8)]))

    with factory() as session:
        result = verify_decision_chain(session)
        assert result.valid is True
        assert result.unsealed_count == 0
        assert result.sealed_count == 8
