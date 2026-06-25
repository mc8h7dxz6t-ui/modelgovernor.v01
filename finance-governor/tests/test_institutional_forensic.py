"""Institutional++ forensic baseline — all five platforms."""
from __future__ import annotations

import sys
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from platforms.common.event_store import AppendOnlyEventStore
from platforms.common.forensic_audit import audit_event_store, audit_platform_metrics_zero_violations
from platforms.common.platform_metrics import get_platform_metrics


class TestPlatformBaseline:
    """Gold standard Platform Baseline checks."""

    @pytest.mark.parametrize(
        "module_path,app_attr",
        [
            ("platforms.algofreeze.main", "app"),
            ("platforms.wire_match.main", "app"),
            ("platforms.subledger_sync.main", "app"),
            ("platforms.asset_ledger.main", "app"),
            ("platforms.credit_govern.main", "app"),
        ],
    )
    def test_healthz_readyz(self, module_path: str, app_attr: str):
        mod = __import__(module_path, fromlist=[app_attr])
        client = TestClient(getattr(mod, app_attr))
        assert client.get("/healthz").status_code == 200
        assert client.get("/readyz").status_code == 200

    @pytest.mark.parametrize(
        "module_path,app_attr",
        [
            ("platforms.algofreeze.main", "app"),
            ("platforms.wire_match.main", "app"),
            ("platforms.subledger_sync.main", "app"),
            ("platforms.asset_ledger.main", "app"),
            ("platforms.credit_govern.main", "app"),
        ],
    )
    def test_metrics_prometheus_format(self, module_path: str, app_attr: str):
        mod = __import__(module_path, fromlist=[app_attr])
        client = TestClient(getattr(mod, app_attr))
        r = client.get("/metrics")
        assert r.status_code == 200
        assert "# TYPE" in r.text

    def test_append_only_event_chain(self):
        store = AppendOnlyEventStore()
        for i in range(5):
            store.append(
                platform="test",
                event_type="TEST",
                operation_id=f"op-{i}",
                payload={"seq": i},
            )
        result = audit_event_store(store, "test")
        assert result.passed
        assert result.checks["chain_valid"]

    def test_zero_violation_counters_at_boot(self):
        # Fresh process — violation counters must be 0
        snap = get_platform_metrics().snapshot()
        assert snap.get("frozen_egress_violation_total", 0) == 0
        assert snap.get("wire_sent_below_threshold_total", 0) == 0


class TestAlgoFreezeInvariants:
    @pytest.fixture()
    def client(self):
        import platforms.algofreeze.main as main_mod
        from platforms.algofreeze.deploy_registry import DeployRegistry
        from platforms.algofreeze.metrics_hooks import record_unfreeze

        record_unfreeze(main_mod._controller)
        main_mod._registry = DeployRegistry()
        main_mod._registry.register_approval("approved-sha-v1", approved_by="test", ci_pipeline_id="test")
        from platforms.algofreeze.main import app

        return TestClient(app)

    def test_no_egress_violation_when_frozen(self, client):
        client.post("/orders", json={"order_id": "v1", "runtime_sha": "bad-sha"})
        blocked = client.post("/orders", json={"order_id": "v2", "runtime_sha": "approved-sha-v1"})
        assert blocked.status_code == 403
        metrics = client.get("/metrics").text
        assert "frozen_egress_violation_total 0" in metrics.replace("\n", " ") or "frozen_egress_violation_total\n0" in metrics

    def test_freeze_event_chain(self, client):
        client.post("/orders", json={"order_id": "chain-1", "runtime_sha": "wrong"})
        events = client.get("/internal/events/recent").json()
        assert events["chain_valid"] is True
        assert any(e["event_type"] == "FREEZE" for e in events["events"])


class TestWireMatchInvariants:
    @pytest.fixture()
    def client(self):
        from platforms.common.mesh_guard import get_mesh_guard
        from platforms.wire_match.main import app

        get_mesh_guard().set_algo_active()
        return TestClient(app)

    def test_no_float_in_wire_path(self, client):
        r = client.post(
            "/wire/evaluate",
            json={
                "wire_id": "f1",
                "beneficiary_name": "Revlon Lenders Group",
                "beneficiary_account": "US12REV001",
                "reference": "x",
                "amount": "not-decimal",
            },
        )
        assert r.status_code == 422

    def test_held_never_sent(self, client):
        r = client.post(
            "/wire/send",
            json={
                "wire_id": "held-1",
                "beneficiary_name": "Wrong Corp",
                "beneficiary_account": "US99",
                "amount": "7800000.00",
            },
        )
        assert r.json()["status"] == "HELD"
        snap = get_platform_metrics().snapshot()
        assert snap.get("wire_sent_below_threshold_total", 0) == 0


class TestCreditGovernInvariants:
    @pytest.fixture()
    def client(self):
        from platforms.common.mesh_guard import get_mesh_guard
        from platforms.credit_govern.main import app

        get_mesh_guard().set_algo_active()
        return TestClient(app)

    def test_duplicate_application_id(self, client):
        payload = {
            "application_id": "dup-1",
            "exposure_amount": "1000.00",
            "model_version": "credit-v3.2.1",
            "feature_snapshot_hash": "hash-a",
        }
        client.post("/governed/decision", json=payload)
        second = client.post("/governed/decision", json=payload)
        assert second.json()["status"] == "DUPLICATE"

    def test_exposure_never_negative(self, client):
        client.post("/admin/desks", json={"desk_id": "tiny", "cap_amount": "100.00"})
        r = client.post(
            "/governed/decision",
            json={
                "application_id": "over-1",
                "desk_id": "tiny",
                "exposure_amount": "500.00",
                "model_version": "credit-v3.2.1",
                "feature_snapshot_hash": "hash-b",
            },
        )
        assert r.json()["status"] == "DENIED"
        audit = audit_platform_metrics_zero_violations()
        assert audit.checks.get("negative_balance_detected_total", True)
