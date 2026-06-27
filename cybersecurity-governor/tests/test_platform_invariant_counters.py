"""Per-wedge invariant counter tests — zero error budget signals."""
from __future__ import annotations

import os

from fastapi.testclient import TestClient

from platforms.common.platform_metrics import get_platform_counters


def _reset(platform: str) -> None:
    counters = get_platform_counters(platform)
    with counters._lock:
        for key in counters._counters:
            counters._counters[key] = 0


def test_egress_denied_increments_counter():
    os.environ["CG_SPINE_ENABLED"] = "false"
    _reset("egress_govern")
    from platforms.egress_govern.main import app

    client = TestClient(app)
    response = client.post(
        "/egress/evaluate",
        json={"flow_id": "ec-1", "destination_host": "malware.bad"},
    )
    assert response.status_code == 403
    snap = get_platform_counters("egress_govern").snapshot()
    assert snap["egress_denied_total"] >= 1


def test_threat_blocked_increments_counter():
    os.environ["CG_SPINE_ENABLED"] = "false"
    _reset("threat_proxy")
    from platforms.threat_proxy.main import app

    client = TestClient(app)
    response = client.post(
        "/threat/score",
        json={
            "request_id": "tc-1",
            "payload_entropy": 0.95,
            "anomaly_signals": ["exfil_pattern"],
            "data_class": "pci",
        },
    )
    assert response.status_code == 403
    snap = get_platform_counters("threat_proxy").snapshot()
    assert snap["threat_blocked_total"] >= 1


def test_posture_drift_increments_counter():
    os.environ["CG_SPINE_ENABLED"] = "false"
    _reset("posture_reconcile")
    from platforms.posture_reconcile.main import app

    client = TestClient(app)
    response = client.post(
        "/posture/ingest",
        json={"asset_id": "host-drift", "critical_cves": 5, "patch_lag_days": 90},
    )
    assert response.status_code == 422
    snap = get_platform_counters("posture_reconcile").snapshot()
    assert snap["posture_drift_total"] >= 1
