"""AssetLedger platform tests."""
import sys
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from platforms.asset_ledger.asset_registry import Asset, AssetRegistry
from platforms.asset_ledger.depreciation_engine import DepreciationEngine
from platforms.asset_ledger.main import app
from platforms.asset_ledger.reg_table_sync import RegTableSync


@pytest.fixture()
def client():
    return TestClient(app)


def test_book_value_never_negative():
    reg = AssetRegistry()
    with pytest.raises(ValueError):
        reg.register(Asset("a1", Decimal("-1")))


def test_reg_table_version_pinned():
    registry = AssetRegistry()
    registry.register(Asset("fleet-1", Decimal("120000")))
    engine = DepreciationEngine(registry, RegTableSync())
    charge = engine.run_period_charge("fleet-1", "2026-06", "UK:hmrc")
    assert charge.reg_table_version == "hmrc-2026-q1"
    assert charge.book_value_after < Decimal("120000")


def test_one_depreciation_per_period():
    registry = AssetRegistry()
    registry.register(Asset("fleet-2", Decimal("50000")))
    engine = DepreciationEngine(registry, RegTableSync())
    engine.run_period_charge("fleet-2", "2026-06", "UK:hmrc")
    with pytest.raises(ValueError, match="duplicate"):
        engine.run_period_charge("fleet-2", "2026-06", "UK:hmrc")


def test_depreciate_api(client):
    client.post("/assets/register", json={"asset_id": "api-1", "book_value": "10000.00"})
    r = client.post("/assets/depreciate", json={"asset_id": "api-1", "period": "2026-06"})
    assert r.status_code == 200
    assert r.json()["reg_table_version"] == "hmrc-2026-q1"
    asset = client.get("/assets/api-1").json()
    assert Decimal(asset["book_value"]) < Decimal("10000")
