"""Circuit breaker tests for Cybersecurity Governor dependency protection."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SIDECAR = ROOT / "spine" / "sidecar"
sys.path.insert(0, str(SIDECAR))

from app.circuit_breaker import CircuitOpenError, DependencyCircuitBreaker, reset_circuit_breaker
from app.config import Settings


def _settings(**overrides) -> Settings:
    base = {
        "database_url": "sqlite:///:memory:",
        "redis_url": "redis://invalid:9/0",
        "cg_internal_tokens": "token",
        "circuit_breaker_failure_threshold": 2,
        "circuit_breaker_window_seconds": 60,
        "circuit_breaker_open_seconds": 30,
    }
    base.update(overrides)
    return Settings(**base)


def test_circuit_opens_after_failure_threshold() -> None:
    reset_circuit_breaker()
    breaker = DependencyCircuitBreaker(_settings())
    for _ in range(2):
        breaker.record_failure("redis")
    try:
        breaker.assert_closed("redis")
        assert False, "expected CircuitOpenError"
    except CircuitOpenError:
        pass


def test_circuit_recovers_after_success() -> None:
    reset_circuit_breaker()
    breaker = DependencyCircuitBreaker(_settings())
    breaker.record_failure("redis")
    breaker.record_failure("redis")
    breaker.record_success("redis")
    breaker.assert_closed("redis")
