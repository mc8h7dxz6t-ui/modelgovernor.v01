"""Witness silence detection — detects telemetry gaps (log erasure / agent kill)."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class WitnessState:
    last_seen: dict[str, datetime] = field(default_factory=dict)
    silence_threshold_seconds: int = 300

    def record(self, source: str, now: datetime | None = None) -> None:
        self.last_seen[source] = now or datetime.now(timezone.utc)

    def silent_sources(self, now: datetime | None = None) -> list[str]:
        ts = now or datetime.now(timezone.utc)
        silent: list[str] = []
        for source, seen_at in self.last_seen.items():
            if (ts - seen_at).total_seconds() > self.silence_threshold_seconds:
                silent.append(source)
        return silent
