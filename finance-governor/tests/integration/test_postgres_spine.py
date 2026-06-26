"""Postgres-backed decision chain verification."""
from __future__ import annotations

HEADERS = {"x-internal-token": "test-token"}


def test_postgres_chain_and_anchor(pg_sidecar_client):
    client, engine = pg_sidecar_client
    facets = {"amount": "1000.00", "currency": "USD"}
    r = client.post(
        "/crystallize",
        headers=HEADERS,
        json={
            "platform": "wire_match",
            "operation_id": "pg-chain-1",
            "account_id": "desk-default",
            "risk_tier": "high",
            "facets": facets,
            "policy_id": "wire-critical-us",
        },
    )
    assert r.status_code == 200, r.text
    crystal_id = r.json()["crystal_id"]
    c = client.post(
        "/commit",
        headers=HEADERS,
        json={"crystal_id": crystal_id, "facets": facets, "committed_exposure": "0"},
    )
    assert c.status_code == 200

    verify = client.get("/internal/decisions/verify-chain", headers=HEADERS)
    assert verify.json()["valid"] is True

    anchor = client.post("/internal/decisions/anchor-head", headers=HEADERS)
    assert anchor.status_code == 200
    body = anchor.json()
    assert body["anchored"] is True
    assert body["head_hash"]


def test_postgres_negative_balance_invariant(pg_sidecar_client):
    client, _ = pg_sidecar_client
    facets = {"amount": "1.00"}
    r = client.post(
        "/crystallize",
        headers=HEADERS,
        json={
            "platform": "wire_match",
            "operation_id": "pg-cap-1",
            "account_id": "desk-default",
            "risk_tier": "high",
            "facets": facets,
            "reserved_exposure": "999999999999.00",
        },
    )
    assert r.status_code == 409
