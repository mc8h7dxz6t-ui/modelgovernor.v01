"""H1 — concurrent claim append stays chain-valid under Postgres advisory lock."""
from __future__ import annotations

import os
import sys
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy.orm import sessionmaker

ROOT = Path(__file__).resolve().parents[1]
SIDECAR = ROOT / "spine" / "sidecar"
if str(SIDECAR) not in sys.path:
    sys.path.insert(0, str(SIDECAR))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

spine_core_root = ROOT.parent / "governor-spine-core"
if str(spine_core_root) not in sys.path:
    sys.path.insert(0, str(spine_core_root))

pytestmark = pytest.mark.skipif(
    not os.getenv("POSTGRES_TEST_URL"),
    reason="POSTGRES_TEST_URL required",
)


def test_concurrent_claim_append_chain_stays_valid(pg_engine, clean_pg_tables) -> None:
    from app.claim_events import append_claim_event
    from app.claim_seal import verify_claim_chain

    factory = sessionmaker(bind=pg_engine)

    def append_one(op_suffix: str) -> None:
        with factory() as session:
            append_claim_event(
                session,
                operation_id=f"conc-{op_suffix}",
                crystal_id=None,
                account_id="carrier-default",
                event_type="RESERVED",
                reserve_delta=Decimal("1.00"),
                metadata={"probe": op_suffix},
            )
            session.commit()

    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(append_one, [str(i) for i in range(8)]))

    with factory() as session:
        result = verify_claim_chain(session)
        assert result.valid is True
        assert result.unsealed_count == 0
        assert result.sealed_count == 8
