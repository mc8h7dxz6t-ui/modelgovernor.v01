"""Toxiproxy-backed chaos tests for Finance Ops Finals."""
from __future__ import annotations

import os
import time
from decimal import Decimal
from pathlib import Path
import sys

import pytest
import requests
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from sidecar.app.config import Settings
from sidecar.app.ledger import reserve_operation
from sidecar.app.schemas import ReserveRequest
from tests.integration.conftest import _apply_migrations

TOXIPROXY_API = os.getenv("TOXIPROXY_API", "http://localhost:8474")
PROXY_NAME = "postgres"


def _postgres_url() -> str:
    url = os.getenv("POSTGRES_TEST_URL")
    if not url:
        pytest.skip(
            "POSTGRES_TEST_URL not set — start docker-compose.chaos.yml and export "
            "POSTGRES_TEST_URL=postgresql+psycopg://postgres:postgres@localhost:5435/mg_chaos"
        )
    return url


def _reset_proxy() -> None:
    try:
        requests.delete(f"{TOXIPROXY_API}/proxies/{PROXY_NAME}/toxics", timeout=2)
    except requests.RequestException:
        pytest.skip("toxiproxy API unavailable")


def _add_latency(ms: int) -> None:
    requests.post(
        f"{TOXIPROXY_API}/proxies/{PROXY_NAME}/toxics",
        json={"name": "latency", "type": "latency", "attributes": {"latency": ms, "jitter": 10}},
        timeout=5,
    ).raise_for_status()


@pytest.fixture(scope="module")
def chaos_engine():
    database_url = _postgres_url()
    _reset_proxy()
    engine = create_engine(database_url, future=True)
    _apply_migrations(engine)
    yield engine
    _reset_proxy()
    engine.dispose()


def _settings(database_url: str) -> Settings:
    return Settings(
        database_url=database_url,
        redis_url="redis://example/0",
        sidecar_internal_tokens="test-token",
        default_trace_cap_amount=Decimal("100"),
        drift_absolute_tolerance=Decimal("1"),
        drift_ratio_tolerance=Decimal("1"),
        manual_approval_cost_threshold=Decimal("1000000"),
        default_run_budget_amount=Decimal("1000000"),
        default_session_budget_amount=Decimal("1000000"),
        default_user_budget_amount=Decimal("1000000"),
        default_tenant_budget_amount=Decimal("1000000"),
        db_pool_size=3,
        db_max_overflow=2,
        db_pool_timeout_seconds=5,
        db_pool_recycle_seconds=300,
    )


def test_finance_ops_survives_toxiproxy_latency(chaos_engine) -> None:
    _reset_proxy()
    _add_latency(250)
    settings = _settings(str(chaos_engine.url))
    factory = sessionmaker(bind=chaos_engine, autoflush=False, autocommit=False, future=True)

    with factory() as session:
        session.execute(
            text(
                """
                INSERT INTO user_wallets (user_id, balance, active)
                VALUES ('chaos-user', 100, TRUE)
                ON CONFLICT (user_id) DO UPDATE SET balance = 100, active = TRUE
                """
            )
        )

    t0 = time.perf_counter()
    with factory() as session:
        reserve_operation(
            session,
            settings,
            ReserveRequest(
                user_id="chaos-user",
                trace_id="chaos-trace",
                idempotency_key="chaos-op",
                model="gpt-4o-mini",
                estimated_cost=Decimal("5"),
            ),
        )
    elapsed_ms = (time.perf_counter() - t0) * 1000
    assert elapsed_ms >= 200

    with Session(chaos_engine) as session:
        balance = session.execute(
            text("SELECT balance FROM user_wallets WHERE user_id = 'chaos-user'")
        ).scalar_one()
    assert Decimal(str(balance)) == Decimal("95.000000")


def test_finance_ops_toxiproxy_timeout_recovers_on_reset(chaos_engine) -> None:
    _reset_proxy()
    requests.post(
        f"{TOXIPROXY_API}/proxies/{PROXY_NAME}/toxics",
        json={"name": "timeout", "type": "timeout", "attributes": {"timeout": 0}},
        timeout=5,
    ).raise_for_status()

    settings = _settings(str(chaos_engine.url))
    factory = sessionmaker(bind=chaos_engine, autoflush=False, autocommit=False, future=True)

    with pytest.raises(Exception):
        with factory() as session:
            reserve_operation(
                session,
                settings,
                ReserveRequest(
                    user_id="chaos-user",
                    trace_id="chaos-trace-2",
                    idempotency_key="chaos-op-2",
                    model="gpt-4o-mini",
                    estimated_cost=Decimal("1"),
                ),
            )

    _reset_proxy()
    with factory() as session:
        reserve_operation(
            session,
            settings,
            ReserveRequest(
                user_id="chaos-user",
                trace_id="chaos-trace-2",
                idempotency_key="chaos-op-3",
                model="gpt-4o-mini",
                estimated_cost=Decimal("1"),
            ),
        )
