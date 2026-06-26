"""AlgoFreeze — feed heartbeat monitor."""
from __future__ import annotations

from dataclasses import dataclass, field
from time import monotonic


@dataclass
class FeedHeartbeat:
    max_gap_seconds: float = 2.0
    _last_packet_at: float = field(default_factory=monotonic)

    def record_packet(self) -> None:
        self._last_packet_at = monotonic()

    def is_degraded(self) -> bool:
        if self._last_packet_at is None:
            return True
        return (monotonic() - self._last_packet_at) > self.max_gap_seconds
