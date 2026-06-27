"""Shadow / enforce intercept gate — zero-brick guarantee for inline deployment.

Gold standard:
- SHADOW: evaluate fully; on failure or timeout → ALLOW + structured audit (never block prod).
- ENFORCE: on failure → DENY; on evaluator crash/timeout → DENY (fail closed on authorize).
- Latency SLO tracked; optional async metric emission does not block passthrough in SHADOW.
"""
from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, TypeVar

from .metrics import get_counters

logger = logging.getLogger(__name__)

T = TypeVar("T")


class EnforcementMode(str, Enum):
    SHADOW = "SHADOW"
    ENFORCE = "ENFORCE"


@dataclass(frozen=True)
class PolicyConfig:
    mode: EnforcementMode = EnforcementMode.SHADOW
    latency_slo_ms: float = 50.0
    evaluator_timeout_ms: float = 45.0


@dataclass(frozen=True)
class InterceptMetrics:
    crystal_id: str
    tenant_id: str
    domain: str
    mode_evaluated: str
    passed: bool
    latency_ms: float
    slo_breached: bool
    error: str | None = None
    action: str = "ALLOW"

    def to_dict(self) -> dict[str, Any]:
        return {
            "crystal_id": self.crystal_id,
            "tenant_id": self.tenant_id,
            "domain": self.domain,
            "mode_evaluated": self.mode_evaluated,
            "passed": self.passed,
            "latency_ms": self.latency_ms,
            "slo_breached": self.slo_breached,
            "error": self.error,
            "action": self.action,
        }


@dataclass
class InterceptResult:
    action: str
    reason: str | None
    metrics: InterceptMetrics


_evaluator_pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="governor-eval")


def _run_with_timeout(
    fn: Callable[[], bool],
    timeout_seconds: float,
) -> tuple[bool, str | None]:
    future = _evaluator_pool.submit(fn)
    try:
        return future.result(timeout=timeout_seconds), None
    except FuturesTimeoutError:
        future.cancel()
        return False, "evaluator_timeout"
    except Exception as exc:
        return False, str(exc)


def execute_intercept_gate(
    *,
    crystal_id: str,
    tenant_id: str,
    domain: str,
    policy: PolicyConfig,
    core_validation: Callable[[], bool],
) -> InterceptResult:
    """
    Run inline governance evaluation with shadow-safe passthrough semantics.

    SHADOW + any failure → ALLOW (log warning, increment metrics).
    ENFORCE + validation failure → DENY.
    ENFORCE + evaluator error/timeout → DENY (fail closed on authorize path).
    """
    start = time.perf_counter()
    timeout_s = max(policy.evaluator_timeout_ms, 1.0) / 1000.0

    passed, error = _run_with_timeout(core_validation, timeout_s)

    elapsed_ms = (time.perf_counter() - start) * 1000.0
    slo_breached = elapsed_ms > policy.latency_slo_ms
    mode = policy.mode.value

    counters = get_counters()
    counters.increment("governor_intercept_total")
    if slo_breached:
        counters.increment("governor_intercept_slo_breach_total")
        logger.warning(
            "governor intercept SLO breach crystal=%s latency_ms=%.2f slo_ms=%.2f",
            crystal_id,
            elapsed_ms,
            policy.latency_slo_ms,
        )

    if error:
        logger.error(
            "governor intercept evaluator error crystal=%s mode=%s error=%s",
            crystal_id,
            mode,
            error,
        )
        counters.increment("governor_intercept_evaluator_error_total")

    if passed:
        metrics = InterceptMetrics(
            crystal_id=crystal_id,
            tenant_id=tenant_id,
            domain=domain,
            mode_evaluated=mode,
            passed=True,
            latency_ms=round(elapsed_ms, 3),
            slo_breached=slo_breached,
            error=error,
            action="ALLOW",
        )
        counters.increment("governor_intercept_allow_total")
        return InterceptResult(action="ALLOW", reason=None, metrics=metrics)

    if policy.mode == EnforcementMode.ENFORCE:
        metrics = InterceptMetrics(
            crystal_id=crystal_id,
            tenant_id=tenant_id,
            domain=domain,
            mode_evaluated=mode,
            passed=False,
            latency_ms=round(elapsed_ms, 3),
            slo_breached=slo_breached,
            error=error,
            action="DENY",
        )
        counters.increment("governor_intercept_deny_total")
        reason = error or "invariant_policy_violation"
        logger.error("governor ENFORCE DENY crystal=%s reason=%s", crystal_id, reason)
        return InterceptResult(action="DENY", reason=reason, metrics=metrics)

    metrics = InterceptMetrics(
        crystal_id=crystal_id,
        tenant_id=tenant_id,
        domain=domain,
        mode_evaluated=mode,
        passed=False,
        latency_ms=round(elapsed_ms, 3),
        slo_breached=slo_breached,
        error=error,
        action="ALLOW",
    )
    counters.increment("governor_intercept_shadow_passthrough_total")
    logger.warning(
        "governor SHADOW PASSTHROUGH crystal=%s error=%s",
        crystal_id,
        error or "validation_failed",
    )
    return InterceptResult(
        action="ALLOW",
        reason="shadow_mode_passthrough",
        metrics=metrics,
    )


def policy_from_settings() -> PolicyConfig:
    from .config import get_settings

    settings = get_settings()
    mode_str = getattr(settings, "enforcement_mode", "SHADOW").upper()
    try:
        mode = EnforcementMode(mode_str)
    except ValueError:
        mode = EnforcementMode.SHADOW
    return PolicyConfig(
        mode=mode,
        latency_slo_ms=float(getattr(settings, "enforcement_latency_slo_ms", 50.0)),
        evaluator_timeout_ms=float(getattr(settings, "enforcement_evaluator_timeout_ms", 45.0)),
    )
