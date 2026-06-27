"""Prometheus metrics on Finance Governor sidecar."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
SIDECAR = ROOT / "spine" / "sidecar"
sys.path.insert(0, str(SIDECAR))

from tests.conftest_spine import spine_db  # noqa: F401


@pytest.fixture()
def client(spine_db):
    from app.main import app

    return TestClient(app)


def test_prometheus_public_scrape(client):
    r = client.get("/metrics/prometheus")
    assert r.status_code == 200
    assert "fg_invariant_events_total" in r.text


def test_authenticated_metrics_includes_counters(client):
    r = client.get("/metrics", headers={"x-internal-token": "test-token"})
    assert r.status_code == 200
    assert "fg_invariant_events_total" in r.text
