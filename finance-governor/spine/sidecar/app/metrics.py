from __future__ import annotations

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
    "ledger_chain_verification_failed_total",
    "decision_event_sealed_total",
    "decision_chain_anchor_recorded_total",
    "decision_chain_anchor_s3_ok_total",
    "decision_chain_anchor_s3_failed_total",
    "drift_enforced_total",
    "drift_tolerated_total",
)


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


_counters = InvariantCounters()


def get_counters() -> InvariantCounters:
    return _counters
