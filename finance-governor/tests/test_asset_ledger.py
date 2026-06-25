"""AssetLedger platform tests."""
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from platforms.asset_ledger.main import app, _charged_periods, _events, _registry


@pytest.fixture(autouse=True)
def reset_state():
    _registry._assets.clear()
    _events.clear()
    _charged_periods.clear()
    yield


@pytest.fixture()
def client():
    return TestClient(app)


def test_register_and_get_asset(client):
    r = client.post(
        "/assets",
        json={
            "asset_id": "rack-1",
            "description": "Server rack",
            "acquisition_cost": "120000.00",
            "useful_life_months": 60,
        },
    )
    assert r.status_code == 200
    g = client.get("/assets/rack-1")
    assert g.json()["book_value"] == "120000.00"


def test_depreciation_run_charges_once(client):
    client.post(
        "/assets",
        json={
            "asset_id": "rack-1",
            "description": "Server rack",
            "acquisition_cost": "120000.00",
            "useful_life_months": 60,
        },
    )
    r1 = client.post("/depreciation/run", json={"period": "2026-06"})
    r2 = client.post("/depreciation/run", json={"period": "2026-06"})
    assert len(r1.json()["charges"]) == 1
    assert len(r2.json()["charges"]) == 0


def test_depreciation_reduces_book_value(client):
    client.post(
        "/assets",
        json={
            "asset_id": "rack-1",
            "description": "Server rack",
            "acquisition_cost": "120000.00",
            "useful_life_months": 60,
        },
    )
    client.post("/depreciation/run", json={"period": "2026-06"})
    g = client.get("/assets/rack-1")
    assert float(g.json()["book_value"]) < 120000.0
    assert float(g.json()["accumulated_depreciation"]) > 0


def test_events_list(client):
    client.post(
        "/assets",
        json={
            "asset_id": "rack-1",
            "description": "Server rack",
            "acquisition_cost": "120000.00",
        },
    )
    client.post("/depreciation/run", json={"period": "2026-06"})
    events = client.get("/events")
    assert len(events.json()) >= 1


def test_asset_not_found(client):
    r = client.get("/assets/missing")
    assert r.status_code == 404
