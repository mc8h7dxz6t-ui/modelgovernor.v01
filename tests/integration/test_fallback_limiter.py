"""Local fallback limiter tests when Redis is unavailable."""
from __future__ import annotations

import pytest

from sidecar.app.config import Settings
from sidecar.app.fallback_limiter import LocalFallbackLimiter
from sidecar.app.guardrail_errors import RateLimitExceeded
from sidecar.app.metrics import get_counters


def _settings(**overrides) -> Settings:
    base = {
        "database_url": "sqlite:///:memory:",
        "redis_url": "redis://example/0",
        "sidecar_internal_tokens": "token",
        "fallback_rate_limit_per_minute": 100,
        "fallback_max_user_inflight": 100,
        "fallback_max_trace_depth": 100,
        "fallback_global_tokens_per_second": 1.0,
        "fallback_token_bucket_capacity": 2.0,
    }
    base.update(overrides)
    return Settings(**base)


def test_local_fallback_token_bucket_limits_burst() -> None:
    limiter = LocalFallbackLimiter()
    settings = _settings(fallback_token_bucket_capacity=1.0, fallback_global_tokens_per_second=0.1)
    get_counters().reset()

    limiter.check_reserve(
        settings=settings, user_id="u1", trace_id="t1", idempotency_key="op-1"
    )
    with pytest.raises(RateLimitExceeded):
        limiter.check_reserve(
            settings=settings, user_id="u1", trace_id="t2", idempotency_key="op-2"
        )
    assert get_counters().snapshot()["local_fallback_rate_limit_total"] >= 1


def test_guardrails_use_fallback_when_redis_down(monkeypatch) -> None:
    monkeypatch.setattr("redis.from_url", lambda *args, **kwargs: (_ for _ in ()).throw(ConnectionError("down")))
    from sidecar.app.guardrails import GuardrailService

    service = GuardrailService(
        _settings(
            fallback_rate_limit_per_minute=1,
            fallback_max_user_inflight=10,
            fallback_token_bucket_capacity=10.0,
            fallback_global_tokens_per_second=100.0,
        )
    )
    get_counters().reset()
    service.check_reserve(user_id="u1", trace_id="t1", idempotency_key="op-1")
    with pytest.raises(RateLimitExceeded):
        service.check_reserve(user_id="u1", trace_id="t1", idempotency_key="op-2")
    assert get_counters().snapshot()["local_fallback_reserve_total"] == 1
