"""Finance Governor sidecar — invariant counters with Prometheus export."""
from __future__ import annotations

import json
import threading
from typing import Dict

_COUNTER_NAMES = (
    "crystallize_success_total",
    "crystallize_idempotent_replay_total",
    "commit_success_total",
    "surprise_commit_blocked_total",
    "crystal_fingerprint_mismatch_total",
    "crystal_horizon_strand_total",
    "crystal_mesh_block_total",
    "negative_balance_detected_total",
    "exposure_cap_overrun_detected_total",
    "duplicate_commit_anomaly_total",
    "regulatory_audit_violation_total",
    "regulatory_audit_diagnostic_entered_total",
    "reconciler_horizon_strand_total",
    "reconciler_expired_total",
    "crystal_manual_strand_total",
    "ledger_chain_verification_failed_total",
    "decision_event_sealed_total",
    "decision_chain_anchor_recorded_total",
    "decision_chain_anchor_s3_ok_total",
    "decision_chain_anchor_s3_failed_total",
    "drift_enforced_total",
    "drift_tolerated_total",
    "guardrail_degraded_total",
    "provider_circuit_open_total",
    "attribution_identity_mismatch_total",
)

_registered = False


class InvariantCounters:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counters: Dict[str, int] = {n: 0 for n in _COUNTER_NAMES}

    def increment(self, name: str, delta: int = 1) -> None:
        with self._lock:
            self._counters[name] = self._counters.get(name, 0) + delta

    def snapshot(self) -> Dict[str, int]:
        with self._lock:
            return dict(self._counters)

    def to_json(self) -> str:
        return json.dumps(self.snapshot(), sort_keys=True)


class InvariantCounterCollector:
    def __init__(self, counters: InvariantCounters) -> None:
        self._counters = counters

    def collect(self):
        from prometheus_client.core import CounterMetricFamily

        metric = CounterMetricFamily(
            "fg_invariant_events_total",
            "Finance Governor spine invariant counters.",
            labels=["event"],
        )
        for name, value in self._counters.snapshot().items():
            metric.add_metric([name], float(value))
        yield metric


_counters = InvariantCounters()


def get_counters() -> InvariantCounters:
    global _registered
    if not _registered:
        try:
            from prometheus_client import REGISTRY

            REGISTRY.register(InvariantCounterCollector(_counters))
            _registered = True
        except (ImportError, ValueError):
            pass
    return _counters
