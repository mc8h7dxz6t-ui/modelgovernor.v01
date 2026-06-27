"""LineageIngest — Falco/Tetragon/generic structural DAG tier."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel

from platforms.common.lineage import LineageEdge, is_critical_edge, normalize_lineage
from platforms.common.platform_sdk import GovernedPlatform, spine_health_payload

app = FastAPI(title="lineage-ingest", version="0.1.0")
_GOVERNED = GovernedPlatform("lineage_ingest")


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
    payload = spine_health_payload("lineage_ingest")
    payload["edge_count"] = len(_local.edges)
    return payload


@app.get("/readyz")
def readyz() -> dict:
    return healthz()


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
    edge_id = _local.add(edge)
    crystal_id = None
    if is_critical_edge(edge):
        facets = {
            "source_system": edge.source_system,
            "edge_type": edge.edge_type,
            "child_ref": edge.child_ref,
            "principal_id": edge.principal_id,
            "lineage_decision": "CRITICAL",
            "severity": edge.severity,
        }
        crystal_id = _GOVERNED.govern_operation(
            f"lineage-{edge_id}",
            facets,
            decision="CRITICAL",
            reserve_amount="0",
            outcome="critical",
        )
    return IngestResponse(
        accepted=True,
        edge_type=edge.edge_type,
        child_ref=edge.child_ref,
        severity=edge.severity,
        edge_id=edge_id,
        crystal_id=crystal_id,
    )


@app.get("/dag/{principal_id}")
def dag(principal_id: str, limit: int = 50) -> list[dict[str, Any]]:
    return _local.dag(principal_id, limit)
