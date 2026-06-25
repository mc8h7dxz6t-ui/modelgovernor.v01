"""Append-only platform event store (standalone mode)."""
from __future__ import annotations

import hashlib
import json
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class PlatformEvent:
    seq: int
    platform: str
    event_type: str
    operation_id: str
    payload: dict[str, Any]
    event_hash: str
    prev_hash: str
    created_at: str


class AppendOnlyEventStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._events: list[PlatformEvent] = []
        self._head_hash = "GENESIS"

    def append(
        self,
        *,
        platform: str,
        event_type: str,
        operation_id: str,
        payload: dict[str, Any],
    ) -> PlatformEvent:
        with self._lock:
            seq = len(self._events) + 1
            created_at = datetime.now(timezone.utc).isoformat()
            body = {
                "seq": seq,
                "platform": platform,
                "event_type": event_type,
                "operation_id": operation_id,
                "payload": payload,
                "prev_hash": self._head_hash,
                "created_at": created_at,
            }
            event_hash = hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()
            event = PlatformEvent(
                seq=seq,
                platform=platform,
                event_type=event_type,
                operation_id=operation_id,
                payload=payload,
                event_hash=event_hash,
                prev_hash=self._head_hash,
                created_at=created_at,
            )
            self._events.append(event)
            self._head_hash = event_hash
            return event

    def recent(self, limit: int = 50) -> list[PlatformEvent]:
        with self._lock:
            return list(self._events[-limit:])

    def verify_chain(self) -> bool:
        with self._lock:
            prev = "GENESIS"
            for event in self._events:
                if event.prev_hash != prev:
                    return False
                body = {
                    "seq": event.seq,
                    "platform": event.platform,
                    "event_type": event.event_type,
                    "operation_id": event.operation_id,
                    "payload": event.payload,
                    "prev_hash": event.prev_hash,
                    "created_at": event.created_at,
                }
                expected = hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()
                if expected != event.event_hash:
                    return False
                prev = event.event_hash
            return True
