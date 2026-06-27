"""Tests for shadow/enforce intercept gate — zero-brick semantics."""
from __future__ import annotations

import time

from sidecar.app.enforcement_mode import (
    EnforcementMode,
    PolicyConfig,
    execute_intercept_gate,
)
from sidecar.app.metrics import get_counters


def test_shadow_passthrough_on_validation_failure() -> None:
    get_counters().reset()
    result = execute_intercept_gate(
        crystal_id="c1",
        tenant_id="tenant-a",
        domain="CYBER",
        policy=PolicyConfig(mode=EnforcementMode.SHADOW),
        core_validation=lambda: False,
    )
    assert result.action == "ALLOW"
    assert result.reason == "shadow_mode_passthrough"
    assert result.metrics.passed is False
    assert get_counters().snapshot()["governor_intercept_shadow_passthrough_total"] == 1


def test_enforce_denies_on_validation_failure() -> None:
    get_counters().reset()
    result = execute_intercept_gate(
        crystal_id="c2",
        tenant_id="tenant-a",
        domain="FINANCE",
        policy=PolicyConfig(mode=EnforcementMode.ENFORCE),
        core_validation=lambda: False,
    )
    assert result.action == "DENY"
    assert result.metrics.passed is False


def test_shadow_passthrough_on_evaluator_timeout() -> None:
    get_counters().reset()

    def slow() -> bool:
        time.sleep(0.2)
        return True

    result = execute_intercept_gate(
        crystal_id="c3",
        tenant_id="tenant-a",
        domain="MODEL_GOV",
        policy=PolicyConfig(
            mode=EnforcementMode.SHADOW,
            evaluator_timeout_ms=10.0,
        ),
        core_validation=slow,
    )
    assert result.action == "ALLOW"
    assert result.metrics.error == "evaluator_timeout"


def test_enforce_denies_on_evaluator_timeout() -> None:
    get_counters().reset()

    def slow() -> bool:
        time.sleep(0.2)
        return True

    result = execute_intercept_gate(
        crystal_id="c4",
        tenant_id="tenant-a",
        domain="MODEL_GOV",
        policy=PolicyConfig(
            mode=EnforcementMode.ENFORCE,
            evaluator_timeout_ms=10.0,
        ),
        core_validation=slow,
    )
    assert result.action == "DENY"
    assert result.metrics.error == "evaluator_timeout"
