"""Toxiproxy fixtures for Cyber Governor Tier 4 chaos tests."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
import requests
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

ROOT = Path(__file__).resolve().parents[2]
SIDECAR = ROOT / "spine" / "sidecar"
sys.path.insert(0, str(SIDECAR))
sys.path.insert(0, str(ROOT))

from tests.helpers import apply_postgres_migrations, reset_cg_tables

TOXIPROXY_API = os.getenv("TOXIPROXY_API", "http://localhost:8475")
PROXY_NAME = "cg-postgres"
PROXY_LISTEN = "0.0.0.0:5446"
PROXY_UPSTREAM = "cg-postgres-chaos:5432"


def chaos_postgres_url() -> str:
    url = os.getenv("CG_CHAOS_POSTGRES_URL") or os.getenv("CG_POSTGRES_TEST_URL")
    if not url:
        pytest.skip(
            "CG_CHAOS_POSTGRES_URL not set — start docker-compose.chaos.yml and export "
            "CG_CHAOS_POSTGRES_URL=postgresql+psycopg://postgres:postgres@localhost:5446/cg_chaos"
        )
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


def reset_proxy(*, recreate: bool = False) -> None:
    try:
        requests.delete(f"{TOXIPROXY_API}/proxies/{PROXY_NAME}/toxics", timeout=5)
        if recreate:
            requests.delete(f"{TOXIPROXY_API}/proxies/{PROXY_NAME}", timeout=5)
            requests.post(
                f"{TOXIPROXY_API}/proxies",
                json={
                    "name": PROXY_NAME,
                    "listen": PROXY_LISTEN,
                    "upstream": PROXY_UPSTREAM,
                    "enabled": True,
                },
                timeout=5,
            ).raise_for_status()
    except requests.RequestException:
        pytest.skip("toxiproxy API unavailable")


def add_latency(ms: int) -> None:
    requests.post(
        f"{TOXIPROXY_API}/proxies/{PROXY_NAME}/toxics",
        json={"name": "latency", "type": "latency", "attributes": {"latency": ms, "jitter": 10}},
        timeout=5,
    ).raise_for_status()


def add_connection_timeout_toxic() -> None:
    requests.post(
        f"{TOXIPROXY_API}/proxies/{PROXY_NAME}/toxics",
        json={"name": "timeout", "type": "timeout", "attributes": {"timeout": 1}},
        timeout=5,
    ).raise_for_status()


@pytest.fixture(scope="module")
def toxiproxy_engine() -> Engine:
    database_url = chaos_postgres_url()
    reset_proxy()
    engine = create_engine(
        database_url,
        future=True,
        connect_args={"connect_timeout": 3},
        pool_pre_ping=True,
    )
    apply_postgres_migrations(engine)
    reset_cg_tables(engine)
    yield engine
    reset_proxy()
    engine.dispose()


@pytest.fixture()
def clean_toxiproxy_tables(toxiproxy_engine: Engine):
    reset_cg_tables(toxiproxy_engine)
    yield toxiproxy_engine
