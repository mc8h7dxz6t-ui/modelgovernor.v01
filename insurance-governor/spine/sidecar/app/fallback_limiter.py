"""In-process guardrail fallback when Redis is unavailable."""
from __future__ import annotations

import threading
import time
from collections import defaultdict
from typing import TYPE_CHECKING

from .guardrail_errors import InflightLimitExceeded, RateLimitExceeded, TraceDepthExceeded
from .metrics import get_counters

if TYPE_CHECKING:
    from .config import Settings


class LocalFallbackLimiter:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._rate_windows: dict[str, tuple[int, int]] = {}
        self._inflight: dict[str, int] = defaultdict(int)
        self._claim_depth: dict[str, set[str]] = defaultdict(set)
        self._tokens: float = 0.0
        self._last_refill: float = time.monotonic()
        self._initialized = False

    def check_crystallize(
        self,
        *,
        settings: Settings,
        account_id: str,
        claim_id: str,
        operation_id: str,
    ) -> None:
        with self._lock:
            if not self._initialized:
                self._tokens = float(settings.fallback_token_bucket_capacity)
                self._initialized = True
            self._refill_tokens(settings)
            if self._tokens < 1.0:
                get_counters().increment("local_fallback_rate_limit_total")
                raise RateLimitExceeded("local fallback global token bucket exhausted")

            window = int(time.time()) // 60
            prior = self._rate_windows.get(account_id)
            count = 1 if prior is None or prior[0] != window else prior[1] + 1
            self._rate_windows[account_id] = (window, count)
            if count > settings.fallback_rate_limit_per_minute:
                get_counters().increment("local_fallback_rate_limit_total")
                raise RateLimitExceeded(f"local fallback rate limit for account {account_id}")

            claim_ops = self._claim_depth[claim_id]
            claim_ops.add(operation_id)
            if len(claim_ops) > settings.fallback_max_claim_depth:
                get_counters().increment("local_fallback_claim_depth_total")
                raise TraceDepthExceeded(f"local fallback claim depth for {claim_id}")

            inflight = self._inflight[account_id] + 1
            if inflight > settings.fallback_max_account_inflight:
                get_counters().increment("local_fallback_inflight_total")
                raise InflightLimitExceeded(f"local fallback in-flight limit for {account_id}")

            self._inflight[account_id] = inflight
            self._tokens -= 1.0
            get_counters().increment("local_fallback_crystallize_total")

    def release_crystallize(self, *, account_id: str) -> None:
        with self._lock:
            if self._inflight[account_id] > 0:
                self._inflight[account_id] -= 1

    def _refill_tokens(self, settings: Settings) -> None:
        now = time.monotonic()
        elapsed = max(0.0, now - self._last_refill)
        if elapsed <= 0:
            return
        rate = float(settings.fallback_global_tokens_per_second)
        capacity = float(settings.fallback_token_bucket_capacity)
        self._tokens = min(capacity, self._tokens + elapsed * rate)
        self._last_refill = now


_fallback_limiter = LocalFallbackLimiter()


def get_fallback_limiter() -> LocalFallbackLimiter:
    return _fallback_limiter


def reset_fallback_limiter() -> None:
    global _fallback_limiter
    _fallback_limiter = LocalFallbackLimiter()
