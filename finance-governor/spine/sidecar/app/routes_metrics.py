"""Prometheus metrics exposition for Finance Governor sidecar."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse
from sqlalchemy import text

from .auth import require_internal_auth
from .db import get_db_session
from .metrics import get_counters

router = APIRouter(tags=["metrics"])


@router.get("/metrics/prometheus", response_class=PlainTextResponse)
def prometheus_metrics_public() -> str:
    try:
        from prometheus_client import generate_latest

        return generate_latest().decode("utf-8")
    except ImportError:
        return _render_invariant_text()


@router.get("/metrics", response_class=PlainTextResponse, dependencies=[Depends(require_internal_auth)])
def metrics_authenticated() -> str:
    lines = [_render_invariant_text().rstrip()]
    try:
        with get_db_session() as session:
            event_counts = {
                row["event_type"]: row["total"]
                for row in session.execute(
                    text(
                        """
                        SELECT event_type, COUNT(*) AS total
                        FROM decision_events
                        GROUP BY event_type
                        ORDER BY event_type
                        """
                    )
                ).mappings().all()
            }
        lines.append("# HELP fg_decision_events_total Decision events by type.")
        lines.append("# TYPE fg_decision_events_total counter")
        for event_type in sorted(event_counts):
            lines.append(f'fg_decision_events_total{{event_type="{_escape(event_type)}"}} {event_counts[event_type]}')
    except Exception:
        pass
    return "\n".join(lines) + "\n"


def _render_invariant_text() -> str:
    lines = [
        "# HELP fg_invariant_events_total Finance Governor spine invariant counters.",
        "# TYPE fg_invariant_events_total counter",
    ]
    for name, value in sorted(get_counters().snapshot().items()):
        lines.append(f'fg_invariant_events_total{{event="{_escape(name)}"}} {value}')
    return "\n".join(lines) + "\n"


def _escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')
