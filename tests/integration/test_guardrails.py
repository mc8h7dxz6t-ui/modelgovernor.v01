"""Redis guardrail integration tests."""
from __future__ import annotations

from pathlib import Path
import sys

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

fakeredis = pytest.importorskip("fakeredis")

from sidecar.app.config import Settings
from sidecar.app.guardrails import GuardrailService, RateLimitExceeded
from sidecar.app.metrics import get_counters


def _settings(**overrides) -> Settings:
    base = {
        "database_url": "sqlite:///:memory:",
        "redis_url": "redis://fake/0",
        "sidecar_internal_tokens": "token",
        "rate_limit_per_minute": 2,
        "max_trace_depth": 2,
        "max_user_inflight": 1,
    }
    base.update(overrides)
    return Settings(**base)


def test_guardrails_rate_limit_enforced(monkeypatch) -> None:
    fake = fakeredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr("redis.from_url", lambda *args, **kwargs: fake)
    service = GuardrailService(_settings(rate_limit_per_minute=2, max_user_inflight=10))
    get_counters().reset()

    service.check_reserve(user_id="u1", trace_id="t1", idempotency_key="op-1")
    service.release_reserve(user_id="u1")
    service.check_reserve(user_id="u1", trace_id="t1", idempotency_key="op-2")
    service.release_reserve(user_id="u1")

    with pytest.raises(RateLimitExceeded):
        service.check_reserve(user_id="u1", trace_id="t1", idempotency_key="op-3")

    assert get_counters().snapshot()["rate_limit_exceeded_total"] == 1


def test_guardrails_degrade_when_redis_unavailable(monkeypatch) -> None:
    def _boom(*args, **kwargs):
        raise ConnectionError("redis down")

    monkeypatch.setattr("redis.from_url", _boom)
    service = GuardrailService(_settings())
    get_counters().reset()

    service.check_reserve(user_id="u1", trace_id="t1", idempotency_key="op-1")
    assert service.degraded is True
    assert get_counters().snapshot()["guardrail_degraded_total"] >= 1
