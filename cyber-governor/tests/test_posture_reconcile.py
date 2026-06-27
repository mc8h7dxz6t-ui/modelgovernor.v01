"""PostureReconcile platform tests."""
from __future__ import annotations

import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from platforms.posture_reconcile.main import app  # noqa: E402
from platforms.posture_reconcile.posture_policy import PostureBaseline, evaluate_posture  # noqa: E402

_BASELINE = PostureBaseline(
    baseline_id="test",
    min_posture_score=80,
    critical_controls=frozenset({"public_s3_bucket"}),
)


def test_posture_allowed_compliant():
    client = TestClient(app)
    r = client.post(
        "/posture/evaluate",
        json={
            "evaluation_id": "p1",
            "resource_id": "cluster-prod-1",
            "posture_score": 92,
            "failed_controls": [],
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["decision"] == "ALLOWED"
    assert body["posture_state"] == "COMPLIANT"


def test_posture_stranded_critical_control():
    client = TestClient(app)
    r = client.post(
        "/posture/evaluate",
        json={
            "evaluation_id": "p2",
            "resource_id": "cluster-dr-1",
            "posture_score": 85,
            "failed_controls": ["public_s3_bucket"],
        },
    )
    body = r.json()
    assert body["decision"] == "STRANDED"
    assert body["posture_state"] == "STRANDED"


def test_posture_remediate_minor_drift():
    result = evaluate_posture(
        posture_score=88,
        failed_controls=["stale_patch_window"],
        baseline=_BASELINE,
    )
    assert result.decision == "REMEDIATE"
    assert result.posture_state == "DRIFT"
