"""Provider circuit breaker enforcement tests."""
from __future__ import annotations

import pytest

fakeredis = pytest.importorskip("fakeredis")

from sidecar.app.circuit_breaker import CircuitOpenError, ProviderCircuitBreaker
from sidecar.app.config import Settings
from sidecar.app.metrics import get_counters


def _settings(**overrides) -> Settings:
    base = {
        "database_url": "sqlite:///:memory:",
        "redis_url": "redis://fake/0",
        "sidecar_internal_tokens": "token",
        "circuit_breaker_failure_threshold": 2,
        "circuit_breaker_window_seconds": 60,
        "circuit_breaker_open_seconds": 30,
    }
    base.update(overrides)
    return Settings(**base)


def test_circuit_opens_after_failures_and_blocks(monkeypatch) -> None:
    fake = fakeredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr("redis.from_url", lambda *args, **kwargs: fake)
    breaker = ProviderCircuitBreaker(_settings())
    get_counters().reset()

    breaker.record_failure("openai")
    breaker.record_failure("openai")

    with pytest.raises(CircuitOpenError):
        breaker.assert_closed("openai")

    assert get_counters().snapshot()["provider_circuit_open_total"] >= 1


def test_circuit_closes_after_success(monkeypatch) -> None:
    fake = fakeredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr("redis.from_url", lambda *args, **kwargs: fake)
    breaker = ProviderCircuitBreaker(_settings())

    breaker.record_failure("openai")
    breaker.record_failure("openai")
    breaker.record_success("openai")
    breaker.assert_closed("openai")
