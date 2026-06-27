"""Chaos-style resilience — chain integrity under concurrent load."""
from __future__ import annotations

import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SIDECAR = ROOT / "spine" / "sidecar"
sys.path.insert(0, str(SIDECAR))

from tests.helpers import cg_settings, create_sqlite_engine, identity_facets, session_factory


@pytest.fixture()
def chaos_engine(tmp_path):
    from app.db import override_engine

    eng = create_sqlite_engine(tmp_path / "chaos.sqlite3")
    override_engine(eng)
    yield eng


def test_concurrent_crystallize_commit_maintains_valid_chain(chaos_engine):
    from app.commit_ledger import commit_operation, crystallize_operation
    from app.security_seal import verify_security_chain
    from app.threat_ops import assert_threat_ops_invariants
    from app.security_ops import assert_security_ops_invariants

    settings = cg_settings(str(chaos_engine.url))
    Session = session_factory(chaos_engine)
    errors: list[Exception] = []

    def _worker(i: int) -> None:
        try:
            facets = identity_facets(worker=i)
            with Session() as s:
                cr = crystallize_operation(
                    s, settings,
                    platform="identity_gate",
                    operation_id=f"chaos-{i}",
                    account_id="tenant-default",
                    risk_tier="critical",
                    facets=facets,
                )
                crystal_id = cr.crystal_id
            with Session() as s:
                commit_operation(s, crystal_id=crystal_id, facets=facets, outcome="authorized")
        except Exception as exc:
            errors.append(exc)

    with ThreadPoolExecutor(max_workers=12) as pool:
        futures = [pool.submit(_worker, i) for i in range(24)]
        for f in as_completed(futures):
            f.result()

    assert not errors, errors
    with Session() as s:
        chain = verify_security_chain(s)
        assert chain.valid is True
        assert chain.sealed_count >= 48
        assert_security_ops_invariants(s)
        assert_threat_ops_invariants(s)
