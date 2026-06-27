"""Structural DAG lineage normalization — Falco, Tetragon, generic eBPF exports."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class LineageEdge:
    source_system: str
    edge_type: str
    parent_ref: str | None
    child_ref: str
    principal_id: str
    physical_time: datetime
    logical_counter: int = 0
    causal_parent_ids: list[str] = field(default_factory=list)
    severity: str = "standard"
    metadata: dict[str, Any] = field(default_factory=dict)


_CRITICAL_RULES = frozenset(
    {
        "privilege_escalation",
        "terminal shell",
        "modify shell history",
        "delete",
        "connect",
    }
)


def normalize_lineage(source: str, payload: dict[str, Any]) -> LineageEdge:
    key = source.lower().strip()
    if key == "falco":
        return _from_falco(payload)
    if key == "tetragon":
        return _from_tetragon(payload)
    return _from_generic(key, payload)


def is_critical_edge(edge: LineageEdge) -> bool:
    if edge.severity == "critical":
        return True
    haystack = f"{edge.edge_type} {edge.metadata.get('rule', '')}".lower()
    return any(token in haystack for token in _CRITICAL_RULES)


def _from_falco(payload: dict[str, Any]) -> LineageEdge:
    fields = payload.get("output_fields") or {}
    proc = str(fields.get("proc.name") or fields.get("process.name") or "unknown")
    parent = fields.get("proc.pname") or fields.get("process.parent.name")
    user = str(fields.get("user.name") or fields.get("user") or "unknown")
    rule = str(payload.get("rule") or "falco_event")
    priority = str(payload.get("priority") or "Notice")
    severity = "critical" if priority in ("Critical", "Error", "Warning") and "shell" in rule.lower() else "standard"
    ts = _parse_time(payload.get("time") or payload.get("timestamp"))
    child_ref = f"proc:{proc}:{fields.get('proc.pid', fields.get('process.pid', ''))}"
    parent_ref = f"proc:{parent}" if parent else None
    return LineageEdge(
        source_system="falco",
        edge_type="process_exec",
        parent_ref=parent_ref,
        child_ref=child_ref,
        principal_id=user,
        physical_time=ts,
        severity=severity,
        metadata={"rule": rule, "priority": priority, "output": payload.get("output"), "fields": fields},
    )


def _from_tetragon(payload: dict[str, Any]) -> LineageEdge:
    if "process_exec" in payload:
        block = payload["process_exec"]
        proc = block.get("process") or {}
        parent = block.get("parent") or {}
        binary = str(proc.get("binary") or proc.get("arguments") or "unknown")
        parent_bin = str(parent.get("binary") or "") or None
        pod = (proc.get("pod") or {}).get("name") or (proc.get("kubernetes") or {}).get("pod_name")
        principal = str(pod or proc.get("exec_id") or "unknown")
        child_ref = f"exec:{proc.get('exec_id', binary)}"
        parent_ref = f"exec:{parent.get('exec_id', parent_bin)}" if parent_bin or parent.get("exec_id") else None
        return LineageEdge(
            source_system="tetragon",
            edge_type="process_exec",
            parent_ref=parent_ref,
            child_ref=child_ref,
            principal_id=principal,
            physical_time=_parse_time(proc.get("start_time") or payload.get("time")),
            severity="standard",
            metadata={"binary": binary, "parent_binary": parent_bin, "namespace": (proc.get("namespace") or {})},
        )
    if "process_connect" in payload:
        block = payload["process_connect"]
        proc = block.get("process") or {}
        sock = block.get("socket") or block.get("destination") or {}
        dst = str(sock.get("address") or sock.get("ip") or sock.get("port") or "unknown")
        principal = str((proc.get("pod") or {}).get("name") or proc.get("exec_id") or "unknown")
        return LineageEdge(
            source_system="tetragon",
            edge_type="socket_connect",
            parent_ref=f"exec:{proc.get('exec_id', proc.get('binary', ''))}",
            child_ref=f"socket:{dst}",
            principal_id=principal,
            physical_time=_parse_time(payload.get("time")),
            severity="critical",
            metadata={"destination": dst, "binary": proc.get("binary")},
        )
    return _from_generic("tetragon", payload)


def _from_generic(source: str, payload: dict[str, Any]) -> LineageEdge:
    edge_type = str(payload.get("edge_type") or payload.get("event_type") or "generic")
    return LineageEdge(
        source_system=source,
        edge_type=edge_type,
        parent_ref=payload.get("parent_ref"),
        child_ref=str(payload.get("child_ref") or payload.get("resource_id") or "unknown"),
        principal_id=str(payload.get("principal_id") or payload.get("user") or "unknown"),
        physical_time=_parse_time(payload.get("physical_time") or payload.get("timestamp")),
        logical_counter=int(payload.get("logical_counter") or 0),
        causal_parent_ids=list(payload.get("causal_parent_ids") or []),
        severity=str(payload.get("severity") or "standard"),
        metadata={k: v for k, v in payload.items() if k not in {"edge_type", "child_ref", "parent_ref"}},
    )


def _parse_time(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=timezone.utc)
    if isinstance(value, str) and value:
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            pass
    return datetime.now(timezone.utc)
