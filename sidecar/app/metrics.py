"""Thread-safe invariant counter registry for the control plane."""
from __future__ import annotations

import json
import threading
from typing import Dict

_COUNTER_NAMES: tuple[str, ...] = (
    "reserve_success_total",
    "reserve_denied_trace_cap_total",
    "reserve_denied_balance_total",
    "reserve_idempotent_replay_total",
    "trace_cap_overrun_detected_total",
    "negative_wallet_detected_total",
    "duplicate_refund_anomaly_total",
    "duplicate_settlement_anomaly_total",
    "drift_enforced_total",
    "drift_tolerated_total",
    "reconciler_claimed_total",
    "reconciler_expired_total",
    "reconciler_stranded_total",
    "budget_scope_exceeded_total",
    "guardrail_approval_required_total",
    "agent_loop_detected_total",
    "attribution_identity_mismatch_total",
    "guardrail_degraded_total",
    "rate_limit_exceeded_total",
    "trace_depth_exceeded_total",
    "user_inflight_exceeded_total",
    "provider_circuit_open_total",
    "finance_audit_violation_total",
    "finance_audit_diagnostic_entered_total",
    "local_fallback_reserve_total",
    "local_fallback_rate_limit_total",
    "local_fallback_inflight_total",
    "local_fallback_trace_depth_total",
)

_collector_registered = False


class InvariantCounters:
    """Thread-safe named counter registry."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counters: Dict[str, int] = {name: 0 for name in _COUNTER_NAMES}

    def increment(self, name: str, delta: int = 1) -> None:
        with self._lock:
            self._counters[name] = self._counters.get(name, 0) + delta

    def snapshot(self) -> Dict[str, int]:
        with self._lock:
            return dict(self._counters)

    def reset(self) -> None:
        with self._lock:
            for key in list(self._counters):
                self._counters[key] = 0

    def to_json(self, *, indent: int = 2) -> str:
        return json.dumps(self.snapshot(), indent=indent, sort_keys=True)


class InvariantCounterCollector:
    """Expose invariant counters to prometheus_client when installed."""

    def __init__(self, counters: InvariantCounters) -> None:
        self._counters = counters

    def collect(self):
        from prometheus_client.core import CounterMetricFamily

        metric = CounterMetricFamily(
            "modelgovernor_invariant_events_total",
            "Invariant event counters for governance control-plane reliability.",
            labels=["event"],
        )
        for name, value in self._counters.snapshot().items():
            metric.add_metric([name], float(value))
        yield metric


_global_counters = InvariantCounters()


def get_counters() -> InvariantCounters:
    global _collector_registered
    if not _collector_registered:
        try:
            from prometheus_client import REGISTRY

            REGISTRY.register(InvariantCounterCollector(_global_counters))
            _collector_registered = True
        except ImportError:
            pass
    return _global_counters
