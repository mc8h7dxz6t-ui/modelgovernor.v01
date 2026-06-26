"""SubledgerSync platform tests."""
import sys
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from platforms.subledger_sync.fx_snapshot import capture_fx_snapshot
from platforms.subledger_sync.match_engine import IcTransaction, MatchEngine
from platforms.subledger_sync.main import app
from platforms.subledger_sync.txn_hasher import canonical_txn_hash


@pytest.fixture()
def client():
    return TestClient(app)


def test_fx_snapshot_hash_deterministic():
    a = capture_fx_snapshot(base_currency="USD", quote_currency="EUR", rate=Decimal("0.92"))
    b = capture_fx_snapshot(base_currency="USD", quote_currency="EUR", rate=Decimal("0.92"))
    assert a.snapshot_hash != b.snapshot_hash  # fetched_at differs
    assert len(a.snapshot_hash) == 64


def test_mirrored_pair_matched():
    engine = MatchEngine()
    a = IcTransaction("hash-a", "UK", "US", Decimal("-1000.00"), "GBP")
    b = IcTransaction("hash-b", "US", "UK", Decimal("1000.00"), "GBP")
    fx = capture_fx_snapshot(base_currency="GBP", quote_currency="USD", rate=Decimal("1.27"))
    result = engine.match_with_fx(a, b, fx)
    assert result.matched
    assert result.fx_snapshot_hash == fx.snapshot_hash


def test_orphan_sweep():
    engine = MatchEngine()
    txn = IcTransaction("orphan", "UK", "US", Decimal("500"), "GBP")
    engine.ingest(txn)
    assert engine.orphan_count() == 1
    stranded = engine.sweep_orphans()
    assert stranded == 1
    assert engine.orphan_count() == 0


def test_ingest_api_pending_then_match(client):
    base = {
        "amount": "1000.00",
        "currency": "GBP",
        "reference": "IC-001",
        "value_date": "2026-06-01",
        "fx_rate": "1.27",
    }
    r1 = client.post("/ic/ingest", json={"entity_id": "UK", "counterparty_id": "US", **base})
    assert r1.json()["status"] == "PENDING"
    r2 = client.post(
        "/ic/ingest",
        json={"entity_id": "US", "counterparty_id": "UK", "amount": "-1000.00", **{k: v for k, v in base.items() if k != "amount"}},
    )
    assert r2.json()["status"] == "MATCHED"
    assert r2.json()["fx_snapshot_hash"]


def test_txn_hash_canonical():
    h1 = canonical_txn_hash(
        entity_id="A", counterparty_id="B", amount=Decimal("100"), currency="USD", reference="x", value_date="2026-01-01"
    )
    h2 = canonical_txn_hash(
        entity_id="A", counterparty_id="B", amount=Decimal("100"), currency="USD", reference="X", value_date="2026-01-01"
    )
    assert h1 == h2
