"""LineageIngest platform tests."""
from __future__ import annotations

import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from platforms.lineage_ingest.main import app  # noqa: E402


def test_ingest_falco_standalone():
    client = TestClient(app)
    r = client.post(
        "/ingest/falco",
        json={
            "rule": "Terminal shell in container",
            "priority": "Critical",
            "output_fields": {"proc.name": "bash", "user.name": "alice"},
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["accepted"] is True
    assert body["edge_type"] == "process_exec"

    dag = client.get("/dag/alice")
    assert len(dag.json()) >= 1
