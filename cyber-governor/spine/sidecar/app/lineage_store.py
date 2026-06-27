"""Persist structural DAG edges to Postgres (spine system of record)."""
from __future__ import annotations

import json
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from platforms.common.lineage import LineageEdge


def schema_supports_lineage_edges(session: Session) -> bool:
    dialect = session.bind.dialect.name
    if dialect == "postgresql":
        row = session.execute(
            text(
                """
                SELECT 1 FROM information_schema.tables
                WHERE table_name = 'lineage_edges'
                """
            )
        ).first()
        return row is not None
    if dialect == "sqlite":
        row = session.execute(
            text(
                """
                SELECT 1 FROM sqlite_master
                WHERE type = 'table' AND name = 'lineage_edges'
                """
            )
        ).first()
        return row is not None
    return False


def insert_lineage_edge(session: Session, edge: LineageEdge) -> int:
    causal_sql = ":causal" if session.bind.dialect.name == "sqlite" else "CAST(:causal AS jsonb)"
    meta_sql = ":meta" if session.bind.dialect.name == "sqlite" else "CAST(:meta AS jsonb)"
    ts = edge.physical_time.isoformat() if session.bind.dialect.name == "sqlite" else edge.physical_time
    params = {
        "source_system": edge.source_system,
        "edge_type": edge.edge_type,
        "parent_ref": edge.parent_ref,
        "child_ref": edge.child_ref,
        "principal_id": edge.principal_id,
        "physical_time": ts,
        "logical_counter": edge.logical_counter,
        "causal": json.dumps(edge.causal_parent_ids),
        "severity": edge.severity,
        "meta": json.dumps(edge.metadata),
    }
    if session.bind.dialect.name == "sqlite":
        session.execute(
            text(
                f"""
                INSERT INTO lineage_edges (
                    source_system, edge_type, parent_ref, child_ref, principal_id,
                    physical_time, logical_counter, causal_parent_ids, severity, metadata
                ) VALUES (
                    :source_system, :edge_type, :parent_ref, :child_ref, :principal_id,
                    :physical_time, :logical_counter, :causal, :severity, :meta
                )
                """
            ),
            params,
        )
        return int(session.execute(text("SELECT last_insert_rowid()")).scalar_one())

    edge_id = session.execute(
        text(
            f"""
            INSERT INTO lineage_edges (
                source_system, edge_type, parent_ref, child_ref, principal_id,
                physical_time, logical_counter, causal_parent_ids, severity, metadata
            ) VALUES (
                :source_system, :edge_type, :parent_ref, :child_ref, :principal_id,
                :physical_time, :logical_counter, {causal_sql}, :severity, {meta_sql}
            )
            RETURNING edge_id
            """
        ),
        params,
    ).scalar_one()
    return int(edge_id)


def query_lineage_dag(session: Session, principal_id: str, limit: int = 50) -> list[dict[str, Any]]:
    rows = session.execute(
        text(
            """
            SELECT edge_id, source_system, edge_type, parent_ref, child_ref,
                   principal_id, physical_time, severity, metadata
            FROM lineage_edges
            WHERE principal_id = :principal
            ORDER BY physical_time DESC, edge_id DESC
            LIMIT :lim
            """
        ),
        {"principal": principal_id, "lim": limit},
    ).mappings().all()
    return [dict(row) for row in rows]
