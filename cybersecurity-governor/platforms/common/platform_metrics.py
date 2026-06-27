"""Platform invariant counters — zero error budget signals for Cybersecurity Governor wedges."""
from __future__ import annotations

import threading
from typing import Dict, Iterable

_DEFAULT_COUNTER_NAMES = (
    "version_mismatch_freeze_total",
    "frozen_inference_blocked_total",
    "inference_allowed_total",
    "indemnity_social_engineering_blocked_total",
    "indemnity_payee_held_total",
    "indemnity_payee_approved_total",
    "indemnity_fat_finger_held_total",
)

_extra_counters_by_platform: Dict[str, tuple[str, ...]] = {}
_counters_by_platform: Dict[str, "PlatformCounters"] = {}


class PlatformCounters:
    def __init__(self, names: Iterable[str] = _DEFAULT_COUNTER_NAMES) -> None:
        self._lock = threading.Lock()
        self._counters: Dict[str, int] = {n: 0 for n in names}

    def increment(self, name: str, delta: int = 1) -> None:
        with self._lock:
            self._counters[name] = self._counters.get(name, 0) + delta

    def snapshot(self) -> Dict[str, int]:
        with self._lock:
            return dict(self._counters)


def register_platform_counters(platform: str, names: Iterable[str]) -> None:
    merged = tuple(dict.fromkeys((*_DEFAULT_COUNTER_NAMES, *names)))
    _extra_counters_by_platform[platform] = merged
    if platform in _counters_by_platform:
        existing = _counters_by_platform[platform]
        with existing._lock:
            for name in names:
                existing._counters.setdefault(name, 0)


def get_platform_counters(platform: str) -> PlatformCounters:
    if platform not in _counters_by_platform:
        names = _extra_counters_by_platform.get(platform, _DEFAULT_COUNTER_NAMES)
        _counters_by_platform[platform] = PlatformCounters(names)
    return _counters_by_platform[platform]


def render_prometheus_text(platform: str) -> str:
    counters = get_platform_counters(platform)
    lines = [
        "# HELP cg_platform_invariant_events_total Platform invariant counters.",
        "# TYPE cg_platform_invariant_events_total counter",
    ]
    for name, value in sorted(counters.snapshot().items()):
        if value:
            lines.append(
                f'cg_platform_invariant_events_total{{platform="{platform}",event="{name}"}} {value}'
            )
    return "\n".join(lines) + "\n"
