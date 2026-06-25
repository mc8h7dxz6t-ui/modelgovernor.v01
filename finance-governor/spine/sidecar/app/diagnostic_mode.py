"""Cluster diagnostic mode — halt writes, keep reads."""
from __future__ import annotations

import logging
import threading
from typing import Any

from .metrics import get_counters

logger = logging.getLogger(__name__)
_lock = threading.Lock()
_local: dict[str, Any] = {"active": False, "reason": None, "component": None}
_REDIS_KEY = "fg:diagnostic_mode"


def _redis_client():
    try:
        import redis
        from .config import get_settings

        s = get_settings()
        c = redis.from_url(s.redis_url, socket_connect_timeout=0.5, socket_timeout=0.5, decode_responses=True)
        c.ping()
        return c
    except Exception:
        return None


def enter_diagnostic_mode(*, component: str, reason: str) -> None:
    with _lock:
        first = not _local["active"]
        _local.update(active=True, component=component, reason=reason)
        if first:
            get_counters().increment("regulatory_audit_diagnostic_entered_total")
            logger.critical("DIAGNOSTIC MODE component=%s reason=%s", component, reason)
    client = _redis_client()
    if client:
        try:
            client.hset(_REDIS_KEY, mapping={"active": "1", "component": component, "reason": reason})
        except Exception:
            pass


def clear_diagnostic_mode() -> None:
    with _lock:
        _local.update(active=False, reason=None, component=None)
    client = _redis_client()
    if client:
        try:
            client.delete(_REDIS_KEY)
        except Exception:
            pass


def is_diagnostic_mode() -> bool:
    client = _redis_client()
    if client:
        try:
            if client.hget(_REDIS_KEY, "active") == "1":
                return True
        except Exception:
            pass
    with _lock:
        return bool(_local["active"])


def diagnostic_snapshot() -> dict:
    with _lock:
        return {
            "diagnostic_mode": _local["active"],
            "diagnostic_component": _local["component"],
            "diagnostic_reason": _local["reason"],
        }
