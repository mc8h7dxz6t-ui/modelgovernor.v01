"""Toxiproxy-backed chaos tests for Cybersecurity Governor claim ops."""
from __future__ import annotations

import os
import sys
import time
from decimal import Decimal
from pathlib import Path

import pytest
import requests
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

ROOT = Path(__file__).resolve().parents[2]
SIDECAR = ROOT / "spine" / "sidecar"
TESTS = ROOT / "tests"
if str(SIDECAR) not in sys.path:
    sys.path.insert(0, str(SIDECAR))
if str(TESTS) not in sys.path:
    sys.path.insert(0, str(TESTS))

from support.cg_migrations import apply_cg_migrations

TOXIPROXY_API = os.getenv("TOXIPROXY_API", "http://localhost:8475")
PROXY_NAME = "postgres"


def _postgres_url() -> str:
    url = os.getenv("POSTGRES_TEST_URL")
    if not url:
        pytest.skip(
            "POSTGRES_TEST_URL not set — start cybersecurity-governor/docker-compose.chaos.yml and export "
            "POSTGRES_TEST_URL=postgresql+psycopg://postgres:postgres@localhost:5436/cg_chaos"
        )
    return url


def _apply_migrations(engine) -> None:
    apply_cg_migrations(engine)


def _reset_proxy(*, recreate: bool = False) -> None:
    try:
        requests.delete(f"{TOXIPROXY_API}/proxies/{PROXY_NAME}/toxics", timeout=5)
        if recreate:
            requests.delete(f"{TOXIPROXY_API}/proxies/{PROXY_NAME}", timeout=5)
            requests.post(
                f"{TOXIPROXY_API}/proxies",
                json={
                    "name": PROXY_NAME,
                    "listen": "0.0.0.0:5436",
                    "upstream": "cg-postgres-chaos:5432",
                    "enabled": True,
                },
                timeout=5,
            ).raise_for_status()
    except requests.RequestException:
        pytest.skip("toxiproxy API unavailable")


def _add_latency(ms: int) -> None:
    requests.post(
        f"{TOXIPROXY_API}/proxies/{PROXY_NAME}/toxics",
        json={"name": "latency", "type": "latency", "attributes": {"latency": ms, "jitter": 10}},
        timeout=5,
    ).raise_for_status()


def _add_connection_timeout_toxic() -> None:
    requests.post(
        f"{TOXIPROXY_API}/proxies/{PROXY_NAME}/toxics",
        json={"name": "timeout", "type": "timeout", "attributes": {"timeout": 1}},
        timeout=5,
    ).raise_for_status()


@pytest.fixture(scope="module")
def chaos_engine():
    database_url = _postgres_url()
    _reset_proxy()
    engine = create_engine(
        database_url,
        future=True,
        connect_args={"connect_timeout": 3},
        pool_pre_ping=True,
    )
    _apply_migrations(engine)
    yield engine
    _reset_proxy()
    engine.dispose()


def _settings(database_url: str):
    from app.config import Settings

    return Settings(
        database_url=database_url,
        redis_url="redis://example/0",
        cg_internal_tokens="test-token",
        guardrails_enabled=False,
        db_pool_size=3,
        db_max_overflow=2,
        db_pool_timeout_seconds=5,
        db_pool_recycle_seconds=300,
    )


def test_security_ops_survives_toxiproxy_latency(chaos_engine) -> None:
    from app.security_ops import assert_security_ops_invariants
    from app.commit_ledger import crystallize_operation

    from support.cyber_fixtures import EGRESS_PLATFORM, EGRESS_POLICY, egress_facets

    _reset_proxy()
    _add_latency(250)
    settings = _settings(str(chaos_engine.url))
    factory = sessionmaker(bind=chaos_engine, autoflush=False, autocommit=False, future=True)

    t0 = time.perf_counter()
    with factory() as session:
        crystallize_operation(
            session,
            settings,
            platform=EGRESS_PLATFORM,
            operation_id="chaos-flow-1",
            account_id="tenant-default",
            risk_tier="high",
            facets=egress_facets(flow_id="chaos-flow-1"),
            policy_id=EGRESS_POLICY,
            reserved_budget=Decimal("50"),
        )
    elapsed_ms = (time.perf_counter() - t0) * 1000
    assert elapsed_ms >= 200

    with Session(chaos_engine) as session:
        balance = session.execute(
            text(
                """
                SELECT balance FROM security_budget_ledgers
                WHERE account_id = 'tenant-default' AND ledger_type = 'case' AND currency = 'USD'
                """
            )
        ).scalar_one()
        assert Decimal(str(balance)) == Decimal("99999950.000000000000")
        assert_security_ops_invariants(session)


def test_security_ops_toxiproxy_timeout_recovers_on_reset(chaos_engine) -> None:
    from app.commit_ledger import crystallize_operation

    _reset_proxy()
    chaos_engine.dispose()
    _add_connection_timeout_toxic()

    settings = _settings(str(chaos_engine.url))
    factory = sessionmaker(bind=chaos_engine, autoflush=False, autocommit=False, future=True)

    with pytest.raises(Exception):
        with factory() as session:
            crystallize_operation(
                session,
                settings,
                platform=EGRESS_PLATFORM,
                operation_id="chaos-flow-2",
                account_id="tenant-default",
                risk_tier="high",
                facets=egress_facets(flow_id="chaos-flow-2"),
                policy_id=EGRESS_POLICY,
                reserved_budget=Decimal("10"),
            )

    _reset_proxy(recreate=True)
    chaos_engine.dispose()
    with factory() as session:
        crystallize_operation(
            session,
            settings,
            platform=EGRESS_PLATFORM,
            operation_id="chaos-flow-3",
            account_id="tenant-default",
            risk_tier="high",
            facets=egress_facets(flow_id="chaos-flow-3"),
            policy_id=EGRESS_POLICY,
            reserved_budget=Decimal("10"),
        )
