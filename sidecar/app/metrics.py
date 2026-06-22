"""Invariant counters and metrics hooks for the ledger control plane.

This module provides a lightweight, thread-safe counter registry that makes
key reliability conditions observable at runtime and in test/load report
artifacts.  It requires no external dependencies and works both in production
(single-process or via per-pod scraping) and in test harness contexts where
multiple components run in the same Python process.

Usage in production code
------------------------
    from .metrics import get_counters
    get_counters().increment("reserve_success_total")

Usage in tests / load harness
------------------------------
    from sidecar.app.metrics import get_counters
    counters = get_counters()
    counters.reset()
    # ... run operations ...
    report = counters.snapshot()
"""
from __future__ import annotations

import json
import threading
from typing import Dict

_COUNTER_NAMES: tuple[str, ...] = (
    # Reserve path
    "reserve_success_total",
    "reserve_denied_trace_cap_total",
    "reserve_denied_balance_total",
    "reserve_idempotent_replay_total",
    # Invariant violations (should stay zero in a healthy system)
    "trace_cap_overrun_detected_total",
    "negative_wallet_detected_total",
    "duplicate_refund_anomaly_total",
    "duplicate_settlement_anomaly_total",
    # Drift enforcement
    "drift_enforced_total",
    "drift_tolerated_total",
    # Reconciler
    "reconciler_claimed_total",
    "reconciler_expired_total",
    "reconciler_stranded_total",
)


class InvariantCounters:
    """Thread-safe named counter registry.

    All counters start at zero.  Increment with :meth:`increment`, read a
    point-in-time snapshot with :meth:`snapshot`, and reset between test runs
    with :meth:`reset`.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counters: Dict[str, int] = {name: 0 for name in _COUNTER_NAMES}

    def increment(self, name: str, delta: int = 1) -> None:
        """Increment *name* by *delta* (default 1).  Unknown names are created."""
        with self._lock:
            self._counters[name] = self._counters.get(name, 0) + delta

    def snapshot(self) -> Dict[str, int]:
        """Return a copy of the current counter state."""
        with self._lock:
            return dict(self._counters)

    def reset(self) -> None:
        """Reset all counters to zero (useful between test scenarios)."""
        with self._lock:
            for k in list(self._counters):
                self._counters[k] = 0

    def to_json(self, *, indent: int = 2) -> str:
        """Serialize the snapshot to a JSON string for report artifacts."""
        return json.dumps(self.snapshot(), indent=indent, sort_keys=True)


# Module-level singleton — shared across all imports in the same process.
_global_counters = InvariantCounters()


def get_counters() -> InvariantCounters:
    """Return the process-global :class:`InvariantCounters` singleton."""
    return _global_counters
