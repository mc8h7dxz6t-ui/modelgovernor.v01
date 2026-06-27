"""Admin audit log tests."""
from __future__ import annotations

import sys
from pathlib import Path

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[1]
SIDECAR = ROOT / "spine" / "sidecar"
sys.path.insert(0, str(SIDECAR))

from tests.conftest_spine import spine_db  # noqa: F401

HEADERS = {"x-internal-token": "test-token"}


@pytest.fixture()
def client(spine_db):
    from app.main import app

    return TestClient(app)


def test_diagnostic_clear_records_audit(client, spine_db):
    from app.diagnostic_mode import enter_diagnostic_mode

    enter_diagnostic_mode(component="test", reason="audit probe")
    r = client.post("/internal/diagnostic/clear", headers=HEADERS)
    assert r.status_code == 200

    with spine_db.begin() as conn:
        row = conn.execute(
            text("SELECT action, row_hash FROM admin_audit_log ORDER BY audit_id DESC LIMIT 1")
        ).first()
        assert row is not None
        assert row[0] == "DIAGNOSTIC_CLEAR"
        assert row[1] is not None
