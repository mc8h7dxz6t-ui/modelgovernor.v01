"""Platform registry guard — spine rejects unregistered platforms and malformed facets."""
from __future__ import annotations

import json
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from .config import Settings
from .metrics import get_counters


class PlatformGuardError(Exception):
    pass


def _manifest_from_row(row: dict[str, Any]) -> dict[str, Any]:
    raw = row.get("manifest_json")
    if raw is None:
        return {}
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        return json.loads(raw) if raw else {}
    return {}


def assert_platform_allowed(
    session: Session,
    settings: Settings,
    *,
    platform: str,
    facets: dict[str, Any],
) -> None:
    if not settings.platform_registry_enforce:
        return

    row = session.execute(
        text(
            """
            SELECT platform_name, display_name, enabled, manifest_json
            FROM platform_registry
            WHERE platform_name = :p
            """
        ),
        {"p": platform},
    ).mappings().first()

    if not row or not row["enabled"]:
        get_counters().increment("platform_registry_reject_total")
        raise PlatformGuardError(f"platform not registered or disabled: {platform}")

    manifest = _manifest_from_row(dict(row))
    required = manifest.get("required_facet_keys", [])
    missing = [key for key in required if key not in facets]
    if missing:
        get_counters().increment("platform_facet_reject_total")
        raise PlatformGuardError(f"platform {platform} missing facets: {', '.join(missing)}")


def list_registered_platforms(session: Session) -> list[dict[str, Any]]:
    rows = session.execute(
        text(
            """
            SELECT platform_name, display_name, enabled, manifest_json, registered_at
            FROM platform_registry
            ORDER BY platform_name
            """
        )
    ).mappings().all()
    out: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        item["manifest"] = _manifest_from_row(item)
        out.append(item)
    return out
