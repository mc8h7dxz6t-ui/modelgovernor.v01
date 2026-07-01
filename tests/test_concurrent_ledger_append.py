"""H1 — concurrent ledger append stays chain-valid under Postgres advisory lock."""
from __future__ import annotations

import sys
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from pathlib import Path

from sqlalchemy.orm import sessionmaker

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

spine_core_root = REPO_ROOT / "governor-spine-core"
if str(spine_core_root) not in sys.path:
    sys.path.insert(0, str(spine_core_root))


def test_concurrent_ledger_append_chain_stays_valid(pg_engine, clean_pg_tables) -> None:
    from sidecar.app.ledger_events import append_sealed_ledger_event
    from sidecar.app.ledger_seal import verify_ledger_chain

    factory = sessionmaker(bind=pg_engine)

    def append_one(op_suffix: str) -> None:
        with factory() as session:
            append_sealed_ledger_event(
                session,
                idempotency_key=f"conc-{op_suffix}",
                user_id="user-1",
                event_type="RESERVED",
                amount_delta=Decimal("1.000000"),
                metadata={"probe": op_suffix},
            )
            session.commit()

    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(append_one, [str(i) for i in range(8)]))

    with factory() as session:
        result = verify_ledger_chain(session)
        assert result.valid is True
        assert result.unsealed_count == 0
        assert result.sealed_count == 8
