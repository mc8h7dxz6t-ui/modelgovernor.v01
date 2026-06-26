"""Real-time discrepancy reporting."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class DiscrepancyReporter:
    _items: list[dict[str, Any]] = field(default_factory=list)

    def emit(self, *, txn_hash: str, reason: str, metadata: dict | None = None) -> dict:
        item = {
            "txn_hash": txn_hash,
            "reason": reason,
            "metadata": metadata or {},
            "recorded_at": datetime.now(timezone.utc).isoformat(),
        }
        self._items.append(item)
        return item

    def list_recent(self, limit: int = 50) -> list[dict]:
        return list(reversed(self._items[-limit:]))
