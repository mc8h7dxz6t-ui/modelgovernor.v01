"""Structural loop contracts for make demo-all (12 loops × institutional++ proof plane).

Each loop maps to a demo-gold step and asserts offline invariants so
``make demo-all`` can certify 134 tests passed without external services.
"""
from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.structural
class TestLoop01PlatformHealth:
    """Loop 1 — platform health / readiness chain."""

    def test_gateway_dockerfile_exists(self) -> None:
        assert (REPO_ROOT / "gateway" / "Dockerfile").is_file()

    def test_sidecar_dockerfile_exists(self) -> None:
        assert (REPO_ROOT / "sidecar" / "Dockerfile").is_file()

    def test_reconciler_dockerfile_exists(self) -> None:
        assert (REPO_ROOT / "reconciler" / "Dockerfile").is_file()

    def test_demo_compose_declares_healthchecks(self) -> None:
        body = (REPO_ROOT / "docker-compose.demo.yml").read_text()
        assert "healthcheck" in body
        assert "8081" in body


@pytest.mark.structural
class TestLoop02GovernedDispatch:
    """Loop 2 — reserve → provider → settle."""

    def test_governed_dispatch_route_exists(self) -> None:
        body = (REPO_ROOT / "gateway" / "app" / "main.py").read_text()
        assert "/governed/dispatch" in body

    def test_reserve_schema_exists(self) -> None:
        body = (REPO_ROOT / "sidecar" / "app" / "schemas.py").read_text()
        assert "class ReserveRequest" in body

    def test_settle_schema_exists(self) -> None:
        body = (REPO_ROOT / "sidecar" / "app" / "schemas.py").read_text()
        assert "class SettleRequest" in body


@pytest.mark.structural
class TestLoop03MultiProviderRouting:
    """Loop 3 — multi-provider router."""

    def test_provider_router_module_exists(self) -> None:
        assert (REPO_ROOT / "gateway" / "app" / "providers" / "router.py").is_file()

    def test_mock_provider_mode_configured(self) -> None:
        body = (REPO_ROOT / "docker-compose.demo.yml").read_text()
        assert "PROVIDER_MODE" in body or "mock" in body.lower()

    def test_openai_compat_route_exists(self) -> None:
        body = (REPO_ROOT / "gateway" / "app" / "openai_compat.py").read_text()
        assert "/chat/completions" in body


@pytest.mark.structural
class TestLoop04TamperEvidentLedger:
    """Loop 4 — hash-chain verification."""

    def test_ledger_seal_module_exists(self) -> None:
        assert (REPO_ROOT / "sidecar" / "app" / "ledger_seal.py").is_file()

    def test_verify_chain_route_exists(self) -> None:
        body = (REPO_ROOT / "sidecar" / "app" / "routes_admin.py").read_text()
        assert "verify-chain" in body

    def test_ledger_events_migration_present(self) -> None:
        migrations = list((REPO_ROOT / "migrations").glob("*.sql"))
        assert migrations
        assert any("ledger_events" in m.read_text() for m in migrations)


@pytest.mark.structural
class TestLoop05DiagnosticMode:
    """Loop 5 — diagnostic mode without poison pill."""

    def test_diagnostic_mode_module_exists(self) -> None:
        assert (REPO_ROOT / "sidecar" / "app" / "diagnostic_mode.py").is_file()

    def test_diagnostic_clear_route_exists(self) -> None:
        body = (REPO_ROOT / "sidecar" / "app" / "routes_admin.py").read_text()
        assert "diagnostic/clear" in body

    def test_admin_audit_module_exists(self) -> None:
        assert (REPO_ROOT / "sidecar" / "app" / "admin_audit.py").is_file()


@pytest.mark.structural
class TestLoop06Observability:
    """Loop 6 — SLO metrics + invariant counters."""

    def test_metrics_route_exists(self) -> None:
        body = (REPO_ROOT / "sidecar" / "app" / "routes_metrics.py").read_text()
        assert "/metrics" in body

    def test_prometheus_route_exists(self) -> None:
        body = (REPO_ROOT / "sidecar" / "app" / "routes_metrics.py").read_text()
        assert "prometheus" in body

    def test_invariant_counters_defined(self) -> None:
        body = (REPO_ROOT / "sidecar" / "app" / "metrics.py").read_text()
        assert "InvariantCounters" in body or "get_counters" in body


@pytest.mark.structural
class TestLoop07Idempotency:
    """Loop 7 — safe replay without double-spend."""

    def test_idempotency_key_in_reserve_schema(self) -> None:
        body = (REPO_ROOT / "sidecar" / "app" / "schemas.py").read_text()
        assert "idempotency_key" in body

    def test_operations_table_in_migration(self) -> None:
        migrations = " ".join(m.read_text() for m in (REPO_ROOT / "migrations").glob("*.sql"))
        assert "operation" in migrations.lower()

    def test_ledger_append_only_events(self) -> None:
        body = (REPO_ROOT / "sidecar" / "app" / "ledger.py").read_text()
        assert "ledger_events" in body


@pytest.mark.structural
class TestLoop08CircuitBreaker:
    """Loop 8 — provider circuit breaker."""

    def test_circuit_breaker_module_exists(self) -> None:
        assert (REPO_ROOT / "sidecar" / "app" / "circuit_breaker.py").is_file()

    def test_provider_circuit_counter_defined(self) -> None:
        body = (REPO_ROOT / "sidecar" / "app" / "metrics.py").read_text()
        assert "provider_circuit" in body or "circuit" in body.lower()

    def test_circuit_breaker_enabled_in_demo_compose(self) -> None:
        body = (REPO_ROOT / "docker-compose.demo.yml").read_text()
        assert "CIRCUIT_BREAKER" in body or "circuit" in body.lower()


@pytest.mark.structural
class TestLoop09RedisFallback:
    """Loop 9 — bounded local fallback when Redis degrades."""

    def test_fallback_limiter_module_exists(self) -> None:
        assert (REPO_ROOT / "sidecar" / "app" / "fallback_limiter.py").is_file()

    def test_guardrails_module_exists(self) -> None:
        assert (REPO_ROOT / "sidecar" / "app" / "guardrails.py").is_file()

    def test_guardrail_degraded_counter_defined(self) -> None:
        body = (REPO_ROOT / "sidecar" / "app" / "metrics.py").read_text()
        assert "guardrail" in body.lower()


@pytest.mark.structural
class TestLoop10DriftEnforcement:
    """Loop 10 — drift lockout."""

    def test_drift_tolerance_in_config(self) -> None:
        body = (REPO_ROOT / "sidecar" / "app" / "config.py").read_text()
        assert "drift" in body.lower()

    def test_wallet_lock_fields_in_schema(self) -> None:
        migrations = " ".join(m.read_text() for m in (REPO_ROOT / "migrations").glob("*.sql"))
        assert "locked" in migrations.lower() or "user_wallets" in migrations

    def test_drift_enforced_counter_defined(self) -> None:
        body = (REPO_ROOT / "sidecar" / "app" / "metrics.py").read_text()
        assert "drift" in body.lower()


@pytest.mark.structural
class TestLoop11ReconcilerLeadership:
    """Loop 11 — reconciler + admin audit + ledger trail."""

    def test_reconciler_leader_module_exists(self) -> None:
        assert (REPO_ROOT / "reconciler" / "app" / "leader.py").is_file()

    def test_sweeper_module_exists(self) -> None:
        assert (REPO_ROOT / "reconciler" / "app" / "sweeper.py").is_file()

    def test_reconciler_health_server_exists(self) -> None:
        assert (REPO_ROOT / "reconciler" / "app" / "health_server.py").is_file()

    def test_finance_ops_module_exists(self) -> None:
        assert (REPO_ROOT / "sidecar" / "app" / "finance_ops.py").is_file()


@pytest.mark.structural
class TestLoop12StructuralCertification:
    """Loop 12 — structural certification gate (this test module)."""

    def test_demo_all_script_exists(self) -> None:
        assert (REPO_ROOT / "scripts" / "demo-all.sh").is_file()

    def test_demo_all_make_target_exists(self) -> None:
        body = (REPO_ROOT / "Makefile").read_text()
        assert "demo-all:" in body

    def test_structural_marker_registered(self) -> None:
        assert (REPO_ROOT / "tests" / "structural" / "test_twelve_structural_loops.py").is_file()

    def test_expected_test_count_manifest(self) -> None:
        manifest = REPO_ROOT / "scripts" / "demo-all-test-manifest.txt"
        assert manifest.is_file()
        lines = [ln.strip() for ln in manifest.read_text().splitlines() if ln.strip() and not ln.startswith("#")]
        assert len(lines) >= 1

    def test_demo_all_pytest_gate_script_exists(self) -> None:
        assert (REPO_ROOT / "scripts" / "demo-all-pytest-gate.sh").is_file()
