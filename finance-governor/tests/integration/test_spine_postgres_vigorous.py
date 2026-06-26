"""Finance Governor spine — Postgres Tier 2 integration tests."""
from __future__ import annotations

import sys
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

ROOT = Path(__file__).resolve().parents[2]
FG = Path(__file__).resolve().parents[1]
SIDECAR = FG / "spine" / "sidecar"
sys.path.insert(0, str(SIDECAR))
sys.path.insert(0, str(FG))

FG_TESTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(FG_TESTS))

from conftest_postgres import clean_fg_pg_tables, fg_pg_engine  # noqa: F401

HEADERS = {"x-internal-token": "test-token"}


@pytest.fixture()
def fg_pg_client(fg_pg_engine, clean_fg_pg_tables, monkeypatch):
    from app.config import Settings, get_settings
    from app.db import override_engine

    test_settings = Settings(
        database_url=str(fg_pg_engine.url),
        redis_url="redis://localhost:6380/0",
        fg_internal_tokens="test-token",
    )
    monkeypatch.setattr("app.config.get_settings", lambda: test_settings)
    override_engine(fg_pg_engine)
    from app.main import app

    yield TestClient(app)
    override_engine(fg_pg_engine)


def test_postgres_crystallize_commit_lifecycle(fg_pg_client):
    facets = {"amount": "1000.00", "currency": "USD"}
    r = fg_pg_client.post(
        "/crystallize",
        headers=HEADERS,
        json={
            "platform": "wire_match",
            "operation_id": "pg-wire-1",
            "account_id": "desk-default",
            "risk_tier": "high",
            "facets": facets,
            "policy_id": "wire-critical-us",
            "reserved_exposure": "500.00",
        },
    )
    assert r.status_code == 200, r.text
    crystal_id = r.json()["crystal_id"]

    c = fg_pg_client.post(
        "/commit",
        headers=HEADERS,
        json={
            "crystal_id": crystal_id,
            "facets": facets,
            "committed_exposure": "500.00",
            "outcome": "sent",
        },
    )
    assert c.status_code == 200
    assert c.json()["status"] == "COMMITTED"


def test_postgres_mesh_block_wire_when_algo_frozen(fg_pg_client):
    freeze_facets = {"freeze_state": "FROZEN", "reason": "VERSION_MISMATCH"}
    fg_pg_client.post(
        "/crystallize",
        headers=HEADERS,
        json={
            "platform": "algofreeze",
            "operation_id": "pg-freeze-1",
            "risk_tier": "critical",
            "facets": freeze_facets,
        },
    )
    wire_facets = {"amount": "100.00"}
    wr = fg_pg_client.post(
        "/crystallize",
        headers=HEADERS,
        json={
            "platform": "wire_match",
            "operation_id": "pg-wire-blocked",
            "risk_tier": "high",
            "facets": wire_facets,
        },
    )
    crystal_id = wr.json()["crystal_id"]
    blocked = fg_pg_client.post(
        "/commit",
        headers=HEADERS,
        json={"crystal_id": crystal_id, "facets": wire_facets, "committed_exposure": "0"},
    )
    assert blocked.status_code == 409
    assert "mesh block" in blocked.json()["detail"].lower()


def test_postgres_verify_chain_after_commit(fg_pg_client):
    facets = {"amount": "50.00"}
    r = fg_pg_client.post(
        "/crystallize",
        headers=HEADERS,
        json={
            "platform": "wire_match",
            "operation_id": "pg-chain-1",
            "risk_tier": "low",
            "facets": facets,
        },
    )
    crystal_id = r.json()["crystal_id"]
    fg_pg_client.post(
        "/commit",
        headers=HEADERS,
        json={"crystal_id": crystal_id, "facets": facets, "committed_exposure": "0"},
    )
    verify = fg_pg_client.get("/internal/decisions/verify-chain", headers=HEADERS)
    assert verify.status_code == 200
    body = verify.json()
    assert body["valid"] is True
    assert body["sealed_count"] >= 2
    assert body["head_hash"]


def test_postgres_concurrent_crystallize_same_op_id(fg_pg_engine, clean_fg_pg_tables, monkeypatch):
    from app.commit_ledger import crystallize_operation
    from app.config import Settings
    from app.db import override_engine

    settings = Settings(
        database_url=str(fg_pg_engine.url),
        redis_url="redis://localhost:6380/0",
        fg_internal_tokens="test-token",
    )
    monkeypatch.setattr("app.config.get_settings", lambda: settings)
    override_engine(fg_pg_engine)
    factory = sessionmaker(bind=fg_pg_engine, autoflush=False, autocommit=False, future=True)

    with factory() as session:
        r1 = crystallize_operation(
            session,
            settings,
            platform="wire_match",
            operation_id="race-op",
            account_id="desk-default",
            risk_tier="low",
            facets={"amount": "1.00"},
        )
    with factory() as session:
        r2 = crystallize_operation(
            session,
            settings,
            platform="wire_match",
            operation_id="race-op",
            account_id="desk-default",
            risk_tier="low",
            facets={"amount": "1.00"},
        )
    assert r1.crystal_id == r2.crystal_id
    assert r2.status == "REPLAY"
