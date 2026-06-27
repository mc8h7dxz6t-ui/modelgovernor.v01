"""Prometheus scrape endpoint."""
from __future__ import annotations

import sys
from pathlib import Path

from fastapi.testclient import TestClient
import pytest

ROOT = Path(__file__).resolve().parents[1]
SIDECAR = ROOT / "spine" / "sidecar"
sys.path.insert(0, str(SIDECAR))

from tests.conftest_spine import spine_db  # noqa: F401


@pytest.fixture()
def client(spine_db):
    from app.main import app

    return TestClient(app)


def test_prometheus_metrics(client):
    prometheus_client = pytest.importorskip("prometheus_client")
    assert prometheus_client is not None
    r = client.get("/metrics/prometheus")
    assert r.status_code == 200
    assert b"insurancegovernor_http_requests_total" in r.content
