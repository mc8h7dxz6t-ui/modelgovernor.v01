"""H1 — concurrent security append stays chain-valid under Postgres advisory lock."""
from __future__ import annotations

import sys
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

ROOT = Path(__file__).resolve().parents[1]
SIDECAR = ROOT / "spine" / "sidecar"
if str(SIDECAR) not in sys.path:
    sys.path.insert(0, str(SIDECAR))

spine_core_root = ROOT.parent / "governor-spine-core"
if str(spine_core_root) not in sys.path:
    sys.path.insert(0, str(spine_core_root))


@pytest.fixture()
def clean_security_events(pg_engine, clean_pg_tables):
    with pg_engine.begin() as conn:
        conn.execute(text("TRUNCATE security_chain_verify_checkpoints RESTART IDENTITY CASCADE"))


def test_concurrent_security_append_chain_stays_valid(pg_engine, clean_security_events) -> None:
    from app.security_events import append_security_event
    from app.security_seal import verify_security_chain

    factory = sessionmaker(bind=pg_engine)

    def append_one(op_suffix: str) -> None:
        with factory() as session:
            append_security_event(
                session,
                operation_id=f"conc-{op_suffix}",
                crystal_id=None,
                account_id="tenant-default",
                event_type="RESERVED",
                reserve_delta=Decimal("1.00"),
                metadata={"probe": op_suffix},
            )
            session.commit()

    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(append_one, [str(i) for i in range(8)]))

    with factory() as session:
        result = verify_security_chain(session)
        assert result.valid is True
        assert result.unsealed_count == 0
        assert result.sealed_count == 8
