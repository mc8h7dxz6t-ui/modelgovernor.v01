"""Runtime platform registry — plug-and-play fleet discovery and validation."""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from platforms.common.facet_schemas import validate_facets


class PlatformNotRegisteredError(ValueError):
    pass


class PlatformDisabledError(ValueError):
    pass


@dataclass
class PlatformRecord:
    platform_name: str
    display_name: str
    enabled: bool
    base_url: str | None
    default_policy_id: str | None
    default_risk_tier: str
    facet_schema: dict[str, Any]
    invariant_counters: list[str]


def _parse_json(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, str):
        return json.loads(value) if value else {}
    return value


def _row_to_record(row: dict[str, Any]) -> PlatformRecord:
    return PlatformRecord(
        platform_name=row["platform_name"],
        display_name=row["display_name"],
        enabled=bool(row.get("enabled", True)),
        base_url=row.get("base_url"),
        default_policy_id=row.get("default_policy_id"),
        default_risk_tier=row.get("default_risk_tier") or "high",
        facet_schema=_parse_json(row.get("facet_schema")) or {},
        invariant_counters=list(_parse_json(row.get("invariant_counters")) or []),
    )


def list_platforms(session: Session, *, enabled_only: bool = False) -> list[PlatformRecord]:
    clause = "WHERE enabled = TRUE" if enabled_only else ""
    rows = session.execute(
        text(f"SELECT * FROM platform_registry {clause} ORDER BY platform_name")
    ).mappings().all()
    return [_row_to_record(dict(r)) for r in rows]


def get_platform(session: Session, platform_name: str) -> PlatformRecord | None:
    row = session.execute(
        text("SELECT * FROM platform_registry WHERE platform_name = :p"),
        {"p": platform_name},
    ).mappings().first()
    return _row_to_record(dict(row)) if row else None


def registry_enforced(session: Session) -> bool:
    count = session.execute(text("SELECT COUNT(*) AS c FROM platform_registry")).mappings().first()
    return bool(count and count["c"] > 0)


def assert_platform_allowed(session: Session, platform_name: str) -> PlatformRecord:
    if not registry_enforced(session):
        return PlatformRecord(
            platform_name=platform_name,
            display_name=platform_name,
            enabled=True,
            base_url=None,
            default_policy_id=None,
            default_risk_tier="high",
            facet_schema={},
            invariant_counters=[],
        )
    record = get_platform(session, platform_name)
    if record is None:
        raise PlatformNotRegisteredError(f"platform not registered: {platform_name}")
    if not record.enabled:
        raise PlatformDisabledError(f"platform disabled: {platform_name}")
    return record


def validate_platform_facets(session: Session, platform_name: str, facets: dict[str, Any]) -> None:
    record = assert_platform_allowed(session, platform_name)
    if record.facet_schema:
        validate_facets(platform_name, facets, record.facet_schema)
