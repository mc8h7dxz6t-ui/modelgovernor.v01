"""Toxiproxy-backed chaos tests for Cyber Governor spine ops."""
from __future__ import annotations

import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SIDECAR = ROOT / "spine" / "sidecar"
sys.path.insert(0, str(SIDECAR))

from tests.chaos.conftest import add_connection_timeout_toxic, add_latency, reset_proxy
from tests.helpers import cg_settings, identity_facets, session_factory

pytestmark = pytest.mark.usefixtures("clean_toxiproxy_tables")


def test_crystallize_commit_survives_toxiproxy_latency(toxiproxy_engine) -> None:
    from app.commit_ledger import commit_operation, crystallize_operation
    from app.security_seal import verify_security_chain

    reset_proxy()
    add_latency(250)
    settings = cg_settings(str(toxiproxy_engine.url))
    Session = session_factory(toxiproxy_engine)
    facets = identity_facets()

    t0 = time.perf_counter()
    with Session() as s:
        cr = crystallize_operation(
            s,
            settings,
            platform="identity_gate",
            operation_id="chaos-latency-1",
            account_id="tenant-default",
            risk_tier="critical",
            facets=facets,
            policy_id="identity-critical-us",
        )
        crystal_id = cr.crystal_id
    with Session() as s:
        commit_operation(s, crystal_id=crystal_id, facets=facets, outcome="authorized")
    elapsed_ms = (time.perf_counter() - t0) * 1000
    assert elapsed_ms >= 200

    with Session() as s:
        chain = verify_security_chain(s)
    assert chain.valid is True
    assert chain.sealed_count >= 2


def test_crystallize_commit_timeout_recovers_on_reset(toxiproxy_engine) -> None:
    from app.commit_ledger import commit_operation, crystallize_operation

    reset_proxy()
    toxiproxy_engine.dispose()
    add_connection_timeout_toxic()

    settings = cg_settings(str(toxiproxy_engine.url))
    Session = session_factory(toxiproxy_engine)
    facets = identity_facets()

    with pytest.raises(Exception):
        with Session() as s:
            crystallize_operation(
                s,
                settings,
                platform="identity_gate",
                operation_id="chaos-timeout-1",
                account_id="tenant-default",
                risk_tier="critical",
                facets=facets,
            )

    reset_proxy(recreate=True)
    toxiproxy_engine.dispose()
    with Session() as s:
        cr = crystallize_operation(
            s,
            settings,
            platform="identity_gate",
            operation_id="chaos-timeout-2",
            account_id="tenant-default",
            risk_tier="critical",
            facets=facets,
            policy_id="identity-critical-us",
        )
        crystal_id = cr.crystal_id
    with Session() as s:
        commit_operation(s, crystal_id=crystal_id, facets=facets, outcome="authorized")


def test_security_chain_valid_after_latency_burst(toxiproxy_engine) -> None:
    from app.commit_ledger import commit_operation, crystallize_operation
    from app.security_seal import verify_security_chain
    from app.security_ops import assert_security_ops_invariants
    from app.threat_ops import assert_threat_ops_invariants

    reset_proxy()
    add_latency(120)
    settings = cg_settings(str(toxiproxy_engine.url))
    Session = session_factory(toxiproxy_engine)

    for i in range(5):
        facets = identity_facets(worker=i)
        with Session() as s:
            cr = crystallize_operation(
                s,
                settings,
                platform="identity_gate",
                operation_id=f"chaos-burst-{i}",
                account_id="tenant-default",
                risk_tier="critical",
                facets=facets,
            )
            crystal_id = cr.crystal_id
        with Session() as s:
            commit_operation(s, crystal_id=crystal_id, facets=facets, outcome="authorized")

    with Session() as s:
        chain = verify_security_chain(s)
        assert chain.valid is True
        assert chain.sealed_count >= 10
        assert_security_ops_invariants(s)
        assert_threat_ops_invariants(s)
