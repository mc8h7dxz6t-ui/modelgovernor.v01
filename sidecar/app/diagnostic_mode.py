"""Cluster diagnostic mode — halt automated mutation while keeping ops surfaces alive."""
from __future__ import annotations

import logging
import threading
from typing import Any

from .metrics import get_counters

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_local: dict[str, Any] = {
    "active": False,
    "reason": None,
    "component": None,
}

_REDIS_KEY = "mg:diagnostic_mode"


def _redis_client():
    try:
        import redis
        from .config import get_settings

        settings = get_settings()
        client = redis.from_url(
            settings.redis_url,
            socket_connect_timeout=settings.redis_connect_timeout_seconds,
            socket_timeout=settings.redis_socket_timeout_seconds,
            decode_responses=True,
        )
        client.ping()
        return client
    except Exception:
        return None


def enter_diagnostic_mode(*, component: str, reason: str) -> None:
    with _lock:
        first_entry = not _local["active"]
        _local["active"] = True
        _local["component"] = component
        _local["reason"] = reason
        if first_entry:
            get_counters().increment("finance_audit_diagnostic_entered_total")
            logger.critical(
                "DIAGNOSTIC MODE component=%s reason=%s — automated sweeps/writes halted; "
                "admin read APIs remain available",
                component,
                reason,
            )

    client = _redis_client()
    if client is not None:
        try:
            client.hset(
                _REDIS_KEY,
                mapping={"active": "1", "component": component, "reason": reason},
            )
        except Exception as exc:
            logger.warning("failed to publish diagnostic mode to redis: %s", exc)


def clear_diagnostic_mode() -> None:
    with _lock:
        _local["active"] = False
        _local["reason"] = None
        _local["component"] = None
    client = _redis_client()
    if client is not None:
        try:
            client.delete(_REDIS_KEY)
        except Exception:
            pass


def is_diagnostic_mode() -> bool:
    client = _redis_client()
    if client is not None:
        try:
            active = client.hget(_REDIS_KEY, "active")
            if active == "1":
                return True
        except Exception:
            pass
    with _lock:
        return bool(_local["active"])


def diagnostic_snapshot() -> dict[str, str | bool | None]:
    client = _redis_client()
    if client is not None:
        try:
            data = client.hgetall(_REDIS_KEY)
            if data.get("active") == "1":
                return {
                    "diagnostic_mode": True,
                    "diagnostic_component": data.get("component"),
                    "diagnostic_reason": data.get("reason"),
                }
        except Exception:
            pass
    with _lock:
        return {
            "diagnostic_mode": _local["active"],
            "diagnostic_component": _local["component"],
            "diagnostic_reason": _local["reason"],
        }
