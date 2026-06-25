"""Invariant counters for Finance Governor platforms (zero error budget)."""
from __future__ import annotations

import threading
from typing import Dict

_PLATFORM_COUNTERS = (
    # AlgoFreeze
    "frozen_egress_attempt_total",
    "version_mismatch_freeze_total",
    "feed_degraded_total",
    "freeze_activation_latency_ms",
    # WireMatch
    "wire_sent_below_threshold_total",
    "wire_float_amount_rejected_total",
    "wire_duplicate_idempotency_total",
    "wire_held_total",
    # SubledgerSync
    "fx_snapshot_failed_total",
    "match_tolerance_breach_total",
    "ic_orphan_detected_total",
    "ic_match_success_total",
    # AssetLedger
    "negative_book_value_total",
    "depreciation_duplicate_period_total",
    "reg_table_version_mismatch_total",
    # CreditGovern
    "negative_balance_detected_total",
    "exposure_cap_overrun_total",
    "model_version_mismatch_total",
    "high_risk_auto_expired_total",
    "reserve_before_score_blocked_total",
    # Cross-platform mesh
    "crystal_mesh_block_total",
)


class PlatformMetrics:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counters: Dict[str, int] = {n: 0 for n in _PLATFORM_COUNTERS}
        self._histograms: Dict[str, list[int]] = {"freeze_activation_latency_ms": []}

    def increment(self, name: str, delta: int = 1) -> None:
        with self._lock:
            self._counters[name] = self._counters.get(name, 0) + delta

    def observe(self, name: str, value: int) -> None:
        with self._lock:
            bucket = self._histograms.setdefault(name, [])
            bucket.append(value)
            if len(bucket) > 1000:
                self._histograms[name] = bucket[-1000:]

    def snapshot(self) -> Dict[str, int]:
        with self._lock:
            return dict(self._counters)

    def prometheus_text(self) -> str:
        with self._lock:
            lines = []
            for name, value in sorted(self._counters.items()):
                lines.append(f"# TYPE {name} counter")
                lines.append(f"{name} {value}")
            for name, values in sorted(self._histograms.items()):
                if not values:
                    continue
                lines.append(f"# TYPE {name} summary")
                lines.append(f"{name}_count {len(values)}")
                lines.append(f"{name}_sum {sum(values)}")
            return "\n".join(lines) + "\n"


_metrics = PlatformMetrics()


def get_platform_metrics() -> PlatformMetrics:
    return _metrics
