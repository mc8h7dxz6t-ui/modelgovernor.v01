"""Facet schema validation — institutional++ contract for spine crystallize."""
from __future__ import annotations

from typing import Any

_BUILTIN_SCHEMAS: dict[str, dict[str, Any]] = {
    "wire_match": {
        "required": ["amount"],
        "properties": {
            "amount": {"type": "string"},
            "currency": {"type": "string"},
            "beneficiary_hash": {"type": "string"},
        },
    },
    "algofreeze": {
        "required": ["runtime_sha"],
        "properties": {
            "runtime_sha": {"type": "string"},
            "freeze_state": {"type": "string"},
        },
    },
    "subledger_sync": {
        "required": ["entity_id", "amount", "currency"],
        "properties": {
            "entity_id": {"type": "string"},
            "counterparty_id": {"type": "string"},
            "amount": {"type": "string"},
            "currency": {"type": "string"},
        },
    },
    "asset_ledger": {
        "required": ["asset_id"],
        "properties": {
            "asset_id": {"type": "string"},
            "period": {"type": "string"},
        },
    },
    "credit_govern": {
        "required": ["application_id", "exposure_amount", "model_version_id"],
        "properties": {
            "application_id": {"type": "string"},
            "exposure_amount": {"type": "string"},
            "model_version_id": {"type": "string"},
            "desk_id": {"type": "string"},
        },
    },
}


class FacetValidationError(ValueError):
    pass


def get_builtin_facet_schema(platform: str) -> dict[str, Any] | None:
    return _BUILTIN_SCHEMAS.get(platform)


def validate_facets(platform: str, facets: dict[str, Any], schema: dict[str, Any] | None = None) -> None:
    """Validate facets against a JSON-schema-like contract (required + property types)."""
    spec = schema if schema is not None else _BUILTIN_SCHEMAS.get(platform)
    if not spec:
        return
    required = spec.get("required") or []
    properties = spec.get("properties") or {}
    for key in required:
        if key not in facets:
            raise FacetValidationError(f"platform={platform}: missing required facet '{key}'")
    for key, value in facets.items():
        prop = properties.get(key)
        if not prop:
            continue
        expected = prop.get("type")
        if expected == "string" and not isinstance(value, str):
            raise FacetValidationError(f"platform={platform}: facet '{key}' must be string")
        if expected == "number" and not isinstance(value, (int, float)):
            raise FacetValidationError(f"platform={platform}: facet '{key}' must be number")
        if expected == "boolean" and not isinstance(value, bool):
            raise FacetValidationError(f"platform={platform}: facet '{key}' must be boolean")
