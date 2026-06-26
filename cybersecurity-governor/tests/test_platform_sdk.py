"""Platform SDK and registry guard tests."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
SIDECAR = ROOT / "spine" / "sidecar"
sys.path.insert(0, str(SIDECAR))

from platforms.common.platform_sdk import GovernedPlatform, PlatformManifest, load_registry
from support.cyber_fixtures import EGRESS_PLATFORM, egress_facets


def test_registry_lists_all_platforms() -> None:
    reg = load_registry()
    assert "egress_govern" in reg
    assert "threat_proxy" in reg
    assert "posture_reconcile" in reg


def test_manifest_validates_required_facets() -> None:
    manifest = PlatformManifest.load("egress_govern")
    assert manifest.validate_facets(egress_facets()) == []
    assert "flow_id" in manifest.validate_facets({})


def test_governed_platform_standalone_commit() -> None:
    governed = GovernedPlatform("identity_govern", spine_enabled=False)
    facets = {
        "principal": "sdk-1",
        "workload_sa": "cg-platform-workload",
        "identity_decision": "VERIFIED",
    }
    crystal_id = governed.govern_operation(
        "sdk-1",
        facets,
        decision="VERIFIED",
        reserve_amount="0",
        outcome="verified",
    )
    assert crystal_id is not None


def test_platform_guard_rejects_unregistered(spine_db, monkeypatch) -> None:
    from app.config import Settings, get_settings, override_settings
    from app.db import override_engine
    from app.guardrails import reset_guardrails
    from app.main import app

    override_settings(
        Settings(
            database_url=str(spine_db.url),
            redis_url="redis://example/0",
            cg_internal_tokens="test-token",
            guardrails_enabled=False,
            platform_registry_enforce=True,
        )
    )
    monkeypatch.setattr("app.config.get_settings", get_settings)
    override_engine(spine_db)
    reset_guardrails()

    with TestClient(app) as client:
        response = client.post(
            "/crystallize",
            headers={"x-internal-token": "test-token"},
            json={
                "platform": "unknown_platform",
                "operation_id": "bad-1",
                "facets": {"x": "1"},
            },
        )
        assert response.status_code == 422


def test_platform_guard_rejects_missing_facets(spine_db, monkeypatch) -> None:
    from app.config import Settings, get_settings, override_settings
    from app.db import override_engine
    from app.guardrails import reset_guardrails
    from app.main import app

    override_settings(
        Settings(
            database_url=str(spine_db.url),
            redis_url="redis://example/0",
            cg_internal_tokens="test-token",
            guardrails_enabled=False,
            platform_registry_enforce=True,
        )
    )
    monkeypatch.setattr("app.config.get_settings", get_settings)
    override_engine(spine_db)
    reset_guardrails()

    with TestClient(app) as client:
        response = client.post(
            "/crystallize",
            headers={"x-internal-token": "test-token"},
            json={
                "platform": EGRESS_PLATFORM,
                "operation_id": "bad-2",
                "facets": {},
            },
        )
        assert response.status_code == 422


def test_list_platforms_endpoint(spine_db, monkeypatch) -> None:
    from app.config import Settings, get_settings, override_settings
    from app.db import override_engine
    from app.guardrails import reset_guardrails
    from app.main import app

    override_settings(
        Settings(
            database_url=str(spine_db.url),
            redis_url="redis://example/0",
            cg_internal_tokens="test-token",
            guardrails_enabled=False,
        )
    )
    monkeypatch.setattr("app.config.get_settings", get_settings)
    override_engine(spine_db)
    reset_guardrails()

    with TestClient(app) as client:
        response = client.get("/internal/platforms", headers={"x-internal-token": "test-token"})
        assert response.status_code == 200
        names = {p["platform_name"] for p in response.json()}
        assert EGRESS_PLATFORM in names
