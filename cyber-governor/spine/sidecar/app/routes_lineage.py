"""Internal lineage DAG persistence API."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from .auth import require_internal_auth
from .db import get_db_session
from .lineage_store import insert_lineage_edge, query_lineage_dag, schema_supports_lineage_edges
from .metrics import get_counters

_CG_ROOT = Path(__file__).resolve().parents[3]
if str(_CG_ROOT) not in sys.path:
    sys.path.insert(0, str(_CG_ROOT))
from platforms.common.lineage import LineageEdge, normalize_lineage  # noqa: E402

router = APIRouter(tags=["lineage"], prefix="/internal/lineage")


class LineageIngestRequest(BaseModel):
    source: str
    payload: dict[str, Any] = Field(default_factory=dict)


class LineageIngestResponse(BaseModel):
    edge_id: int
    edge_type: str
    child_ref: str
    severity: str


@router.post("/ingest", response_model=LineageIngestResponse)
def ingest_lineage(request: LineageIngestRequest, _: None = Depends(require_internal_auth)) -> LineageIngestResponse:
    edge = normalize_lineage(request.source, request.payload)
    with get_db_session() as session:
        if not schema_supports_lineage_edges(session):
            raise HTTPException(status_code=503, detail="lineage_edges table unavailable")
        edge_id = insert_lineage_edge(session, edge)
        session.commit()
    get_counters().increment("lineage_edge_ingested_total")
    return LineageIngestResponse(
        edge_id=edge_id,
        edge_type=edge.edge_type,
        child_ref=edge.child_ref,
        severity=edge.severity,
    )


@router.get("/dag/{principal_id}")
def get_lineage_dag(principal_id: str, limit: int = 50, _: None = Depends(require_internal_auth)) -> list:
    with get_db_session() as session:
        if not schema_supports_lineage_edges(session):
            return []
        return query_lineage_dag(session, principal_id, limit=limit)
