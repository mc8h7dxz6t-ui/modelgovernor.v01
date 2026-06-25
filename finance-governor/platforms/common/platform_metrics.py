"""Platform invariant counters — zero error budget signals (Prometheus-compatible)."""
from __future__ import annotations

import threading
from typing import Dict, Iterable

_PLATFORM_COUNTER_NAMES = (
    "frozen_egress_attempt_total",
    "version_mismatch_freeze_total",
    "feed_degraded_total",
    "wire_sent_below_threshold_total",
    "wire_held_total",
    "wire_approved_total",
    "match_tolerance_breach_total",
    "ic_orphan_detected_total",
    "ic_matched_total",
    "fx_snapshot_failed_total",
    "negative_book_value_total",
    "depreciation_duplicate_blocked_total",
    "rail_circuit_open_total",
    "rail_attempt_total",
    "attribution_identity_mismatch_total",
    "model_version_blocked_total",
    "bias_cohort_alert_total",
)

_collector_registered: set[str] = set()
_extra_counters_by_platform: Dict[str, tuple[str, ...]] = {}


class PlatformCounters:
    def __init__(self, names: Iterable[str] = _PLATFORM_COUNTER_NAMES) -> None:
        self._lock = threading.Lock()
        self._counters: Dict[str, int] = {n: 0 for n in names}

    def increment(self, name: str, delta: int = 1) -> None:
        with self._lock:
            self._counters[name] = self._counters.get(name, 0) + delta

    def snapshot(self) -> Dict[str, int]:
        with self._lock:
            return dict(self._counters)


def register_platform_counters(platform: str, names: Iterable[str]) -> None:
    """Register platform-specific invariant counters (plug-and-play extension)."""
    merged = tuple(dict.fromkeys((*_PLATFORM_COUNTER_NAMES, *names)))
    _extra_counters_by_platform[platform] = merged
    if platform in _counters_by_platform:
        existing = _counters_by_platform[platform]
        with existing._lock:
            for name in names:
                existing._counters.setdefault(name, 0)


class PlatformCounterCollector:
    def __init__(self, counters: PlatformCounters, *, platform: str) -> None:
        self._counters = counters
        self._platform = platform

    def collect(self):
        from prometheus_client.core import CounterMetricFamily

        metric = CounterMetricFamily(
            "fg_platform_invariant_events_total",
            "Finance Governor platform invariant counters (zero error budget).",
            labels=["platform", "event"],
        )
        for name, value in self._counters.snapshot().items():
            metric.add_metric([self._platform, name], float(value))
        yield metric


_counters_by_platform: Dict[str, PlatformCounters] = {}


def get_platform_counters(platform: str) -> PlatformCounters:
    if platform not in _counters_by_platform:
        names = _extra_counters_by_platform.get(platform, _PLATFORM_COUNTER_NAMES)
        _counters_by_platform[platform] = PlatformCounters(names)
    counters = _counters_by_platform[platform]
    if platform not in _collector_registered:
        try:
            from prometheus_client import REGISTRY

            REGISTRY.register(PlatformCounterCollector(counters, platform=platform))
            _collector_registered.add(platform)
        except (ImportError, ValueError):
            pass
    return counters


def render_prometheus_text(platform: str) -> str:
    counters = get_platform_counters(platform)
    lines = [
        "# HELP fg_platform_invariant_events_total Platform invariant counters.",
        "# TYPE fg_platform_invariant_events_total counter",
    ]
    for name, value in sorted(counters.snapshot().items()):
        lines.append(f'fg_platform_invariant_events_total{{platform="{platform}",event="{name}"}} {value}')
    return "\n".join(lines) + "\n"
