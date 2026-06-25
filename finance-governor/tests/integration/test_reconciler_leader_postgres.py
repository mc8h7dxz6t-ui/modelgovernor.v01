"""Postgres reconciler leader election."""
from __future__ import annotations

from sqlalchemy.orm import sessionmaker

from tests.support.reconciler_loader import load_reconciler_module


def test_postgres_advisory_lock_exclusive(postgres_engine):
    leader_mod = load_reconciler_module("leader")
    reconciler_leader_session = leader_mod.reconciler_leader_session
    lock_key = leader_mod.RECONCILER_LEADER_LOCK_KEY

    factory = sessionmaker(bind=postgres_engine)
    with factory() as session_a, factory() as session_b:
        with reconciler_leader_session(session_a, lock_key=lock_key) as leader_a:
            assert leader_a is True
            with reconciler_leader_session(session_b, lock_key=lock_key) as leader_b:
                assert leader_b is False
