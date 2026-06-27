"""Normalize security telemetry from common systems into a canonical envelope."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class CanonicalEvent:
    source: str
    event_type: str
    principal_id: str
    resource_id: str
    action: str
    severity: str
    raw_ref: str
    facets: dict[str, Any]


def normalize_event(source: str, payload: dict[str, Any]) -> CanonicalEvent:
    source_key = source.lower().strip()
    if source_key == "okta":
        return _from_okta(payload)
    if source_key in ("cloudtrail", "aws"):
        return _from_cloudtrail(payload)
    return _from_generic(source_key, payload)


def _from_okta(payload: dict[str, Any]) -> CanonicalEvent:
    event_type = str(payload.get("eventType", payload.get("event_type", "unknown")))
    actor = payload.get("actor", {}) or {}
    principal = str(actor.get("alternateId") or actor.get("id") or payload.get("user_id", "unknown"))
    target = (payload.get("target") or [{}])[0] if isinstance(payload.get("target"), list) else {}
    resource = str(target.get("alternateId") or target.get("id") or "okta")
    severity = "critical" if "session" in event_type.lower() or "token" in event_type.lower() else "standard"
    return CanonicalEvent(
        source="okta",
        event_type=event_type,
        principal_id=principal,
        resource_id=resource,
        action=event_type,
        severity=severity,
        raw_ref=str(payload.get("uuid", payload.get("event_id", ""))),
        facets={
            "client_ip": (payload.get("client") or {}).get("ipAddress"),
            "user_agent": (payload.get("client") or {}).get("userAgent"),
            "outcome": (payload.get("outcome") or {}).get("result"),
            "device_fingerprint": payload.get("device_fingerprint"),
        },
    )


def _from_cloudtrail(payload: dict[str, Any]) -> CanonicalEvent:
    detail = payload.get("detail", payload)
    event_name = str(detail.get("eventName", payload.get("eventName", "unknown")))
    principal = str(
        (detail.get("userIdentity") or {}).get("arn")
        or detail.get("principalId")
        or payload.get("principal_id", "unknown")
    )
    resource = str((detail.get("resources") or [{}])[0].get("ARN", detail.get("requestParameters", {}).get("bucketName", "aws")))
    severity = "critical" if event_name in {"DeleteTrail", "StopLogging", "DeleteFunction", "PutBucketPolicy"} else "standard"
    return CanonicalEvent(
        source="cloudtrail",
        event_type=event_name,
        principal_id=principal,
        resource_id=resource,
        action=event_name,
        severity=severity,
        raw_ref=str(detail.get("eventID", payload.get("event_id", ""))),
        facets={
            "source_ip": detail.get("sourceIPAddress"),
            "user_agent": detail.get("userAgent"),
            "error_code": detail.get("errorCode"),
            "request_params": detail.get("requestParameters"),
        },
    )


def _from_generic(source: str, payload: dict[str, Any]) -> CanonicalEvent:
    return CanonicalEvent(
        source=source,
        event_type=str(payload.get("event_type", payload.get("type", "generic"))),
        principal_id=str(payload.get("principal_id", payload.get("user", "unknown"))),
        resource_id=str(payload.get("resource_id", payload.get("resource", "unknown"))),
        action=str(payload.get("action", payload.get("event_type", "observe"))),
        severity=str(payload.get("severity", "standard")),
        raw_ref=str(payload.get("id", payload.get("event_id", ""))),
        facets={k: v for k, v in payload.items() if k not in {"event_type", "type"}},
    )
