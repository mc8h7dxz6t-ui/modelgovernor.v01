"""Toxiproxy chaos tests for Finance Governor spine."""
from __future__ import annotations

import os
import sys
import time
from decimal import Decimal
from pathlib import Path

import pytest
import requests
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

REPO_ROOT = Path(__file__).resolve().parents[3]
FG_ROOT = Path(__file__).resolve().parents[2]
SIDECAR = FG_ROOT / "spine" / "sidecar"
sys.path.insert(0, str(SIDECAR))
sys.path.insert(0, str(FG_ROOT))
sys.path.insert(0, str(REPO_ROOT))

from app.commit_ledger import crystallize_operation
from app.config import Settings
from tests.support.pg_migrations import apply_migrations_to_engine

MIGRATIONS_DIR = FG_ROOT / "migrations"
_MIGRATION_FILES = ["0001_fg_spine_init.sql", "0002_fg_ledger_chain_anchors.sql"]

TOXIPROXY_API = os.getenv("FG_TOXIPROXY_API", os.getenv("TOXIPROXY_API", "http://localhost:8475"))
PROXY_NAME = "postgres"


def _postgres_url() -> str:
    url = os.getenv("FG_POSTGRES_TEST_URL")
    if not url:
        pytest.skip(
            "FG_POSTGRES_TEST_URL not set — start finance-governor/docker-compose.fg-chaos.yml "
            "and export FG_POSTGRES_TEST_URL=postgresql+psycopg://postgres:postgres@localhost:5437/fg_chaos"
        )
    return url


def _reset_proxy(*, recreate: bool = False) -> None:
    try:
        requests.delete(f"{TOXIPROXY_API}/proxies/{PROXY_NAME}/toxics", timeout=5)
        if recreate:
            requests.delete(f"{TOXIPROXY_API}/proxies/{PROXY_NAME}", timeout=5)
            requests.post(
                f"{TOXIPROXY_API}/proxies",
                json={
                    "name": PROXY_NAME,
                    "listen": "0.0.0.0:5437",
                    "upstream": "fg-postgres-chaos:5432",
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
    apply_migrations_to_engine(engine, MIGRATIONS_DIR, _MIGRATION_FILES)
    yield engine
    _reset_proxy()
    engine.dispose()


def _settings(database_url: str) -> Settings:
    return Settings(
        database_url=database_url,
        redis_url="redis://example/0",
        fg_internal_tokens="test-token",
    )


def test_fg_spine_survives_toxiproxy_latency(chaos_engine) -> None:
    _reset_proxy()
    _add_latency(200)
    settings = _settings(str(chaos_engine.url))
    factory = sessionmaker(bind=chaos_engine, autoflush=False, autocommit=False, future=True)

    t0 = time.perf_counter()
    with factory() as session:
        crystallize_operation(
            session,
            settings,
            platform="wire_match",
            operation_id="chaos-1",
            account_id="desk-default",
            risk_tier="low",
            facets={"amount": "100.00"},
            reserved_exposure=Decimal("10"),
            policy_id="wire-critical-us",
        )
    elapsed_ms = (time.perf_counter() - t0) * 1000
    assert elapsed_ms >= 150

    with factory() as session:
        count = session.execute(text("SELECT COUNT(*) FROM governance_crystals")).scalar_one()
    assert int(count) >= 1


def test_fg_spine_recovers_after_proxy_reset(chaos_engine) -> None:
    _reset_proxy(recreate=True)
    settings = _settings(str(chaos_engine.url))
    factory = sessionmaker(bind=chaos_engine, autoflush=False, autocommit=False, future=True)

    with factory() as session:
        result = crystallize_operation(
            session,
            settings,
            platform="wire_match",
            operation_id="chaos-recover-1",
            account_id="desk-default",
            risk_tier="low",
            facets={"amount": "1.00"},
        )
    assert result.status == "CRYSTALLIZED"
