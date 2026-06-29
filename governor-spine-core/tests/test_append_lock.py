"""H1 — chain append advisory lock conformance and runtime behavior."""

from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

from spine_core.append_lock import APPEND_LOCK_REGISTRY, append_lock_conformance_failures
from spine_core.chain_advisory_lock import chain_append_lock
from spine_core.config import CHAIN_APPEND_LOCK_KEYS, GovernorDomain

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def test_h1_all_four_governors_registered():
    assert len(APPEND_LOCK_REGISTRY) == 4
    assert len(CHAIN_APPEND_LOCK_KEYS) == 4


def test_h1_append_lock_conformance_no_failures():
    failures = append_lock_conformance_failures(REPO_ROOT)
    assert failures == [], "H1 append lock gaps:\n" + "\n".join(failures)


def test_chain_append_lock_noop_on_sqlite(tmp_path) -> None:
    from tests.integration.test_ledger_hardening import _bootstrap_schema, _create_test_engine

    engine = _create_test_engine(tmp_path / "lock-noop.sqlite3")
    _bootstrap_schema(engine)
    factory = sessionmaker(bind=engine)
    with factory() as session:
        with chain_append_lock(session, lock_key=CHAIN_APPEND_LOCK_KEYS[GovernorDomain.MODEL]):
            session.execute(text("SELECT 1"))
        session.commit()
