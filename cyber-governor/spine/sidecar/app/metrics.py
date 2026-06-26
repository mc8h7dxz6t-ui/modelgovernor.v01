from __future__ import annotations

import threading
from typing import Dict

_COUNTER_NAMES = (
    "crystallize_success_total",
    "commit_success_total",
    "surprise_authorize_blocked_total",
    "threat_fingerprint_mismatch_total",
    "threat_horizon_strand_total",
    "threat_mesh_block_total",
    "negative_balance_detected_total",
    "exposure_cap_overrun_detected_total",
    "duplicate_commit_anomaly_total",
    "regulatory_audit_violation_total",
    "regulatory_audit_diagnostic_entered_total",
    "reconciler_horizon_strand_total",
    "reconciler_expired_total",
    "security_chain_verification_ok_total",
    "security_chain_verification_failed_total",
    "security_chain_anchor_recorded_total",
    "security_chain_anchor_failed_total",
    "security_chain_anchor_s3_ok_total",
    "security_chain_anchor_s3_failed_total",
    "security_chain_anchor_webhook_ok_total",
    "security_chain_anchor_webhook_failed_total",
    "lineage_edge_ingested_total",
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
