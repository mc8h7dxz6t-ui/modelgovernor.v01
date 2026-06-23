"""Circuit breaker in-process fallback when Redis is unavailable."""
from __future__ import annotations

import pytest

from sidecar.app.circuit_breaker import CircuitOpenError, ProviderCircuitBreaker
from sidecar.app.config import Settings
from sidecar.app.metrics import get_counters


def _settings(**overrides) -> Settings:
    base = {
        "database_url": "sqlite:///:memory:",
        "redis_url": "redis://unreachable/0",
        "sidecar_internal_tokens": "token",
        "circuit_breaker_failure_threshold": 2,
        "circuit_breaker_window_seconds": 60,
        "circuit_breaker_open_seconds": 30,
    }
    base.update(overrides)
    return Settings(**base)


def test_local_fallback_opens_circuit_when_redis_unavailable(monkeypatch) -> None:
    def _fail_connect(*args, **kwargs):
        raise ConnectionError("redis down")

    monkeypatch.setattr("redis.from_url", _fail_connect)
    get_counters().reset()
    breaker = ProviderCircuitBreaker(_settings())

    breaker.record_failure("openai")
    breaker.record_failure("openai")

    with pytest.raises(CircuitOpenError):
        breaker.assert_closed("openai")

    snapshot = get_counters().snapshot()
    assert snapshot.get("provider_circuit_local_fallback_total", 0) >= 1
    assert snapshot.get("provider_circuit_local_fallback_open_total", 0) >= 1
