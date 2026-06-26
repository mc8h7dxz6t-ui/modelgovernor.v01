"""LineageIngest — Falco/Tetragon/generic structural DAG tier (:8106)."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

import httpx
from fastapi import FastAPI
from pydantic import BaseModel, Field

from platforms.common.lineage import LineageEdge, is_critical_edge, normalize_lineage

app = FastAPI(title="lineage-ingest", version="0.1.0")


@dataclass
class LocalLineageStore:
    edges: list[LineageEdge] = field(default_factory=list)

    def add(self, edge: LineageEdge) -> int:
        self.edges.append(edge)
        return len(self.edges)

    def dag(self, principal_id: str, limit: int = 50) -> list[dict[str, Any]]:
        rows = [e for e in self.edges if e.principal_id == principal_id]
        rows.sort(key=lambda e: e.physical_time, reverse=True)
        return [
            {
                "edge_type": e.edge_type,
                "parent_ref": e.parent_ref,
                "child_ref": e.child_ref,
                "principal_id": e.principal_id,
                "physical_time": e.physical_time.isoformat(),
                "severity": e.severity,
                "metadata": e.metadata,
            }
            for e in rows[:limit]
        ]


_local = LocalLineageStore()
_logical_counter = 0


class IngestResponse(BaseModel):
    accepted: bool
    edge_type: str
    child_ref: str
    severity: str
    edge_id: int | None = None
    crystal_id: str | None = None


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok", "edge_count": len(_local.edges)}


@app.post("/ingest/{source}", response_model=IngestResponse)
def ingest(source: str, payload: dict[str, Any]) -> IngestResponse:
    global _logical_counter
    _logical_counter += 1
    edge = normalize_lineage(source, payload)
    edge = LineageEdge(
        source_system=edge.source_system,
        edge_type=edge.edge_type,
        parent_ref=edge.parent_ref,
        child_ref=edge.child_ref,
        principal_id=edge.principal_id,
        physical_time=edge.physical_time,
        logical_counter=_logical_counter,
        causal_parent_ids=edge.causal_parent_ids,
        severity=edge.severity,
        metadata=edge.metadata,
    )
    edge_id = _persist_edge(source, payload, edge)
    crystal_id = None
    if is_critical_edge(edge):
        crystal_id = _crystallize_if_spine(edge, payload)
    return IngestResponse(
        accepted=True,
        edge_type=edge.edge_type,
        child_ref=edge.child_ref,
        severity=edge.severity,
        edge_id=edge_id,
        crystal_id=crystal_id,
    )


@app.get("/dag/{principal_id}")
def dag(principal_id: str, limit: int = 50) -> list:
    if _spine_enabled():
        return _http_dag(principal_id, limit)
    return _local.dag(principal_id, limit)


def _spine_enabled() -> bool:
    return os.environ.get("CG_SPINE_ENABLED", "false").lower() == "true"


def _sidecar_url() -> str:
    return os.environ.get("CG_SIDECAR_URL", "http://localhost:8101").rstrip("/")


def _token() -> str:
    return os.environ.get("CG_INTERNAL_TOKEN", "dev-cg-spine-token-change-me")


def _persist_edge(source: str, payload: dict[str, Any], edge: LineageEdge) -> int:
    if _spine_enabled():
        try:
            with httpx.Client(timeout=10.0) as client:
                r = client.post(
                    f"{_sidecar_url()}/internal/lineage/ingest",
                    headers={"x-internal-token": _token(), "content-type": "application/json"},
                    json={"source": source, "payload": payload},
                )
                r.raise_for_status()
                return int(r.json()["edge_id"])
        except Exception:
            pass
    return _local.add(edge)


def _http_dag(principal_id: str, limit: int) -> list:
    try:
        with httpx.Client(timeout=10.0) as client:
            r = client.get(
                f"{_sidecar_url()}/internal/lineage/dag/{principal_id}",
                headers={"x-internal-token": _token()},
                params={"limit": limit},
            )
            r.raise_for_status()
            return r.json()
    except Exception:
        return _local.dag(principal_id, limit)


def _crystallize_if_spine(edge: LineageEdge, payload: dict[str, Any]) -> str | None:
    if not _spine_enabled():
        return None
    try:
        from platforms.common.spine_adapter import CommitOutcome, SpineAdapter

        operation_id = f"lineage-{edge.source_system}-{edge.logical_counter}"
        facets = {
            "source_system": edge.source_system,
            "edge_type": edge.edge_type,
            "parent_ref": edge.parent_ref,
            "child_ref": edge.child_ref,
            "principal_id": edge.principal_id,
            "severity": edge.severity,
            "logical_counter": edge.logical_counter,
        }
        adapter = SpineAdapter(platform="lineage_ingest", spine_enabled=True)
        crystal = adapter.crystallize(
            operation_id=operation_id,
            risk_tier="critical",
            facets=facets,
            policy_id="lineage-critical-us",
            account_id="tenant-default",
        )
        adapter.commit(
            CommitOutcome(
                operation_id=operation_id,
                crystal_id=crystal.crystal_id,
                facets=facets,
                outcome="witnessed",
            )
        )
        return crystal.crystal_id
    except Exception:
        return None
