"""Redis-backed volatile runtime guardrails for crystallize/commit hot paths."""
from __future__ import annotations

import logging
import time
from functools import lru_cache
from typing import TYPE_CHECKING

from .circuit_breaker import CircuitOpenError, get_circuit_breaker
from .fallback_limiter import get_fallback_limiter, reset_fallback_limiter
from .guardrail_errors import GuardrailError, InflightLimitExceeded, RateLimitExceeded, TraceDepthExceeded
from .metrics import get_counters

if TYPE_CHECKING:
    from .config import Settings

logger = logging.getLogger(__name__)

__all__ = [
    "GuardrailError",
    "GuardrailService",
    "InflightLimitExceeded",
    "RateLimitExceeded",
    "TraceDepthExceeded",
    "get_guardrails",
]


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
            logger.warning("redis guardrails unavailable; using local fallback: %s", exc)
            self._redis = None
            self._degraded = True

    @property
    def degraded(self) -> bool:
        return self._degraded

    def _mark_degraded(self) -> None:
        if not self._degraded:
            self._degraded = True
            get_counters().increment("guardrail_degraded_total")

    def check_crystallize(self, *, account_id: str, claim_id: str, operation_id: str) -> None:
        if self._settings.guardrails_enabled:
            try:
                get_circuit_breaker().assert_closed("redis")
            except CircuitOpenError:
                get_counters().increment("redis_circuit_open_total")
                raise

        if not self._degraded and self._redis is not None:
            try:
                self._check_redis(account_id=account_id, claim_id=claim_id, operation_id=operation_id)
                get_circuit_breaker().record_success("redis")
                return
            except GuardrailError:
                raise
            except Exception as exc:
                logger.warning("redis guardrail check failed; switching to local fallback: %s", exc)
                get_circuit_breaker().record_failure("redis")
                self._mark_degraded()

        get_counters().increment("guardrail_degraded_total")
        get_fallback_limiter().check_crystallize(
            settings=self._settings,
            account_id=account_id,
            claim_id=claim_id,
            operation_id=operation_id,
        )

    def _check_redis(self, *, account_id: str, claim_id: str, operation_id: str) -> None:
        window = int(time.time()) // 60
        rate_key = f"ig:rate:{account_id}:{window}"
        count = int(self._redis.incr(rate_key))
        if count == 1:
            self._redis.expire(rate_key, 120)
        if count > self._settings.rate_limit_per_minute:
            get_counters().increment("rate_limit_exceeded_total")
            raise RateLimitExceeded(f"rate limit exceeded for account {account_id}")

        claim_key = f"ig:claim:{claim_id}:ops"
        self._redis.sadd(claim_key, operation_id)
        self._redis.expire(claim_key, 3600)
        if int(self._redis.scard(claim_key)) > self._settings.max_claim_depth:
            get_counters().increment("claim_depth_exceeded_total")
            raise TraceDepthExceeded(f"claim depth exceeded for {claim_id}")

        inflight_key = f"ig:inflight:{account_id}"
        inflight = int(self._redis.incr(inflight_key))
        if inflight == 1:
            self._redis.expire(inflight_key, self._settings.commit_ttl_seconds + 120)
        if inflight > self._settings.max_account_inflight:
            self._redis.decr(inflight_key)
            get_counters().increment("account_inflight_exceeded_total")
            raise InflightLimitExceeded(f"in-flight limit exceeded for account {account_id}")

    def release_crystallize(self, *, account_id: str) -> None:
        if not self._degraded and self._redis is not None:
            try:
                inflight_key = f"ig:inflight:{account_id}"
                remaining = int(self._redis.decr(inflight_key))
                if remaining < 0:
                    self._redis.set(inflight_key, 0, ex=self._settings.commit_ttl_seconds + 120)
                return
            except Exception as exc:
                logger.warning("redis guardrail release failed; local fallback release: %s", exc)
                self._mark_degraded()
        get_fallback_limiter().release_crystallize(account_id=account_id)

    def redis_status(self) -> dict[str, str | bool]:
        return {
            "degraded": self._degraded,
            "enabled": self._settings.guardrails_enabled,
            "fallback_active": self._degraded,
        }


@lru_cache(maxsize=1)
def get_guardrails() -> GuardrailService:
    from .config import get_settings

    return GuardrailService(get_settings())


def reset_guardrails() -> None:
    from .circuit_breaker import reset_circuit_breaker

    get_guardrails.cache_clear()
    reset_circuit_breaker()
    reset_fallback_limiter()
