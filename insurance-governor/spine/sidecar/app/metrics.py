from __future__ import annotations

import threading
from collections import defaultdict


class MetricsCollector:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counters: dict[str, int] = defaultdict(int)

    def increment(self, name: str, amount: int = 1) -> None:
        with self._lock:
            self._counters[name] += amount

    def snapshot(self) -> dict[str, int]:
        with self._lock:
            return dict(self._counters)


_collector = MetricsCollector()


def get_counters() -> MetricsCollector:
    return _collector
