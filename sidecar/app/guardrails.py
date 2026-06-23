"""Redis-backed volatile runtime guardrails (rate limits, trace depth, in-flight caps).

When Redis is unavailable the sidecar degrades gracefully: ledger correctness is
unchanged and ``guardrail_degraded_total`` is incremented.
"""
from __future__ import annotations

import logging
import time
from functools import lru_cache
from typing import TYPE_CHECKING

from .metrics import get_counters

if TYPE_CHECKING:
    from .config import Settings

logger = logging.getLogger(__name__)


class GuardrailError(Exception):
    """Base class for runtime guardrail denials."""


class RateLimitExceeded(GuardrailError):
    pass


class TraceDepthExceeded(GuardrailError):
    pass


class InflightLimitExceeded(GuardrailError):
    pass


class GuardrailService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._redis = None
        self._degraded = True
        if settings.guardrails_enabled:
            self._connect()

    def _connect(self) -> None:
        try:
            import redis

            client = redis.from_url(
                self._settings.redis_url,
                socket_connect_timeout=self._settings.redis_connect_timeout_seconds,
                socket_timeout=self._settings.redis_socket_timeout_seconds,
                decode_responses=True,
            )
            client.ping()
            self._redis = client
            self._degraded = False
        except Exception as exc:
            logger.warning("redis guardrails unavailable; degrading: %s", exc)
            self._redis = None
            self._degraded = True

    @property
    def degraded(self) -> bool:
        return self._degraded

    def _mark_degraded(self) -> None:
        if not self._degraded:
            self._degraded = True
            get_counters().increment("guardrail_degraded_total")

    def check_reserve(self, *, user_id: str, trace_id: str, idempotency_key: str) -> None:
        if self._degraded or self._redis is None:
            get_counters().increment("guardrail_degraded_total")
            return

        try:
            window = int(time.time()) // 60
            rate_key = f"mg:rate:{user_id}:{window}"
            count = int(self._redis.incr(rate_key))
            if count == 1:
                self._redis.expire(rate_key, 120)
            if count > self._settings.rate_limit_per_minute:
                get_counters().increment("rate_limit_exceeded_total")
                raise RateLimitExceeded(f"rate limit exceeded for user {user_id}")

            trace_key = f"mg:trace:{trace_id}:ops"
            self._redis.sadd(trace_key, idempotency_key)
            self._redis.expire(trace_key, 3600)
            if int(self._redis.scard(trace_key)) > self._settings.max_trace_depth:
                get_counters().increment("trace_depth_exceeded_total")
                raise TraceDepthExceeded(f"trace depth exceeded for {trace_id}")

            inflight_key = f"mg:inflight:{user_id}"
            inflight = int(self._redis.incr(inflight_key))
            if inflight == 1:
                self._redis.expire(inflight_key, self._settings.reserve_ttl_seconds + 120)
            if inflight > self._settings.max_user_inflight:
                self._redis.decr(inflight_key)
                get_counters().increment("user_inflight_exceeded_total")
                raise InflightLimitExceeded(f"in-flight limit exceeded for user {user_id}")
        except GuardrailError:
            raise
        except Exception as exc:
            logger.warning("redis guardrail check failed; degrading: %s", exc)
            self._mark_degraded()

    def release_reserve(self, *, user_id: str) -> None:
        if self._degraded or self._redis is None:
            return
        try:
            inflight_key = f"mg:inflight:{user_id}"
            remaining = int(self._redis.decr(inflight_key))
            if remaining < 0:
                self._redis.set(inflight_key, 0, ex=self._settings.reserve_ttl_seconds + 120)
        except Exception as exc:
            logger.warning("redis guardrail release failed; degrading: %s", exc)
            self._mark_degraded()

    def redis_status(self) -> dict[str, str | bool]:
        return {"degraded": self._degraded, "enabled": self._settings.guardrails_enabled}


@lru_cache(maxsize=1)
def get_guardrails() -> GuardrailService:
    from .config import get_settings

    return GuardrailService(get_settings())
