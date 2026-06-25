"""Platform observability — readyz and metrics."""
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from platforms.subledger_sync.main import app, reset_state


@pytest.fixture(autouse=True)
def _reset():
    reset_state()
    yield


@pytest.fixture()
def client():
    return TestClient(app)


def test_readyz(client):
    r = client.get("/readyz")
    assert r.status_code == 200
    assert r.json()["status"] == "ready"


def test_metrics_endpoint(client):
    r = client.get("/metrics")
    assert r.status_code == 200
    assert "fg_platform_invariant_events_total" in r.text


def test_healthz_includes_pending(client):
    r = client.get("/healthz")
    assert r.status_code == 200
    assert "pending" in r.json()
