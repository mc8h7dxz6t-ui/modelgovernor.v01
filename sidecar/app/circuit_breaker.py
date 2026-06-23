"""Provider dispatch circuit breaker backed by Redis (volatile, non-authoritative)."""
from __future__ import annotations

import logging
import time
from functools import lru_cache
from typing import TYPE_CHECKING

from .metrics import get_counters

if TYPE_CHECKING:
    from .config import Settings

logger = logging.getLogger(__name__)


class CircuitOpenError(Exception):
    pass


class ProviderCircuitBreaker:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._redis = None
        self._degraded = True
        if settings.circuit_breaker_enabled:
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
            logger.warning("circuit breaker redis unavailable; degrading: %s", exc)
            self._redis = None
            self._degraded = True

    def assert_closed(self, provider_name: str) -> None:
        if self._degraded or self._redis is None:
            return
        try:
            open_key = f"mg:circuit:{provider_name}:open"
            if self._redis.exists(open_key):
                get_counters().increment("provider_circuit_open_total")
                raise CircuitOpenError(f"circuit open for provider {provider_name}")
        except CircuitOpenError:
            raise
        except Exception as exc:
            logger.warning("circuit breaker read failed; degrading: %s", exc)
            self._degraded = True

    def record_failure(self, provider_name: str) -> None:
        if self._degraded or self._redis is None:
            return
        try:
            fail_key = f"mg:circuit:{provider_name}:failures"
            count = int(self._redis.incr(fail_key))
            if count == 1:
                self._redis.expire(fail_key, self._settings.circuit_breaker_window_seconds)
            if count >= self._settings.circuit_breaker_failure_threshold:
                open_key = f"mg:circuit:{provider_name}:open"
                self._redis.set(open_key, "1", ex=self._settings.circuit_breaker_open_seconds)
                get_counters().increment("provider_circuit_open_total")
        except Exception as exc:
            logger.warning("circuit breaker failure record failed: %s", exc)
            self._degraded = True

    def record_success(self, provider_name: str) -> None:
        if self._degraded or self._redis is None:
            return
        try:
            self._redis.delete(
                f"mg:circuit:{provider_name}:failures",
                f"mg:circuit:{provider_name}:open",
            )
        except Exception:
            pass


@lru_cache(maxsize=1)
def get_circuit_breaker() -> ProviderCircuitBreaker:
    from .config import get_settings

    return ProviderCircuitBreaker(get_settings())
