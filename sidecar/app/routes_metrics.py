from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse
from sqlalchemy import text

from .auth import require_internal_auth
from .db import get_db_session
from .metrics import get_counters

router = APIRouter(tags=["metrics"])


@router.get("/metrics/prometheus", response_class=PlainTextResponse)
def get_prometheus_metrics() -> str:
    """Unauthenticated scrape surface for process + RED metrics (PodMonitor)."""
    try:
        from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

        return generate_latest().decode("utf-8")
    except ImportError:
        lines = [
            "# HELP modelgovernor_invariant_events_total Process-level invariant counters.",
            "# TYPE modelgovernor_invariant_events_total counter",
        ]
        for event_name, value in sorted(get_counters().snapshot().items()):
            lines.append(
                f'modelgovernor_invariant_events_total{{event="{_escape_label(event_name)}"}} {value}'
            )
        return "\n".join(lines) + "\n"


@router.get(
    "/metrics",
    response_class=PlainTextResponse,
    dependencies=[Depends(require_internal_auth)],
)
def get_metrics() -> str:
    with get_db_session() as session:
        event_counts = {
            row["event_type"]: row["total"]
            for row in session.execute(
                text(
                    """
                    SELECT event_type, COUNT(*) AS total
                    FROM ledger_events
                    GROUP BY event_type
                    ORDER BY event_type
                    """
                )
            ).mappings().all()
        }
        status_counts = {
            row["status"]: row["total"]
            for row in session.execute(
                text(
                    """
                    SELECT status, COUNT(*) AS total
                    FROM escrow_ledger
                    GROUP BY status
                    ORDER BY status
                    """
                )
            ).mappings().all()
        }
        wallet_state_counts = {
            row["state"]: row["total"]
            for row in session.execute(
                text(
                    """
                    SELECT CASE WHEN active THEN 'active' ELSE 'locked' END AS state, COUNT(*) AS total
                    FROM user_wallets
                    GROUP BY state
                    ORDER BY state
                    """
                )
            ).mappings().all()
        }
        trace_state = session.execute(
            text(
                """
                SELECT
                    COUNT(*) AS traces_total,
                    COALESCE(SUM(cap_amount), 0) AS cap_total,
                    COALESCE(SUM(reserved_total), 0) AS reserved_total,
                    COALESCE(SUM(settled_total), 0) AS settled_total
                FROM trace_budget_state
                """
            )
        ).mappings().one()

    lines = [
        "# HELP modelgovernor_ledger_events_total Total ledger events by event type.",
        "# TYPE modelgovernor_ledger_events_total counter",
    ]
    for event_type in sorted(event_counts):
        lines.append(
            f'modelgovernor_ledger_events_total{{event_type="{_escape_label(event_type)}"}} {event_counts[event_type]}'
        )

    lines.extend(
        [
            "# HELP modelgovernor_operations_total Escrow ledger operations by current status.",
            "# TYPE modelgovernor_operations_total gauge",
        ]
    )
    for status in sorted(status_counts):
        lines.append(f'modelgovernor_operations_total{{status="{_escape_label(status)}"}} {status_counts[status]}')

    lines.extend(
        [
            "# HELP modelgovernor_wallets_total Wallet count by lifecycle state.",
            "# TYPE modelgovernor_wallets_total gauge",
        ]
    )
    for state in sorted(wallet_state_counts):
        lines.append(
            f'modelgovernor_wallets_total{{state="{_escape_label(state)}"}} {wallet_state_counts[state]}'
        )

    lines.extend(
        [
            "# HELP modelgovernor_drift_events_total Drift outcomes from settlement finalization.",
            "# TYPE modelgovernor_drift_events_total counter",
            f'modelgovernor_drift_events_total{{state="enforced"}} {event_counts.get("DRIFT_ENFORCED", 0)}',
            f'modelgovernor_drift_events_total{{state="tolerated"}} {event_counts.get("DRIFT_TOLERATED", 0)}',
            "# HELP modelgovernor_failure_events_total Failure-path governance event totals.",
            "# TYPE modelgovernor_failure_events_total counter",
            f'modelgovernor_failure_events_total{{event_type="PROVIDER_TIMEOUT_RECORDED"}} {event_counts.get("PROVIDER_TIMEOUT_RECORDED", 0)}',
            f'modelgovernor_failure_events_total{{event_type="STRANDED_HOLD"}} {event_counts.get("STRANDED_HOLD", 0)}',
            "# HELP modelgovernor_reconciliation_events_total Reconciler and late-settlement correction totals.",
            "# TYPE modelgovernor_reconciliation_events_total counter",
            f'modelgovernor_reconciliation_events_total{{event_type="EXPIRED_SWEEP"}} {event_counts.get("EXPIRED_SWEEP", 0)}',
            f'modelgovernor_reconciliation_events_total{{event_type="STRANDED_HOLD"}} {event_counts.get("STRANDED_HOLD", 0)}',
            f'modelgovernor_reconciliation_events_total{{event_type="RECONCILED_LATE_SETTLE"}} {event_counts.get("RECONCILED_LATE_SETTLE", 0)}',
            "# HELP modelgovernor_trace_budget_state Aggregate trace-budget state summaries.",
            "# TYPE modelgovernor_trace_budget_state gauge",
            f'modelgovernor_trace_budget_state{{field="traces_total"}} {trace_state["traces_total"]}',
            f'modelgovernor_trace_budget_state{{field="cap_total"}} {trace_state["cap_total"]}',
            f'modelgovernor_trace_budget_state{{field="reserved_total"}} {trace_state["reserved_total"]}',
            f'modelgovernor_trace_budget_state{{field="settled_total"}} {trace_state["settled_total"]}',
        ]
    )

    lines.extend(
        [
            "# HELP modelgovernor_invariant_events_total Process-level invariant counters.",
            "# TYPE modelgovernor_invariant_events_total counter",
        ]
    )
    for event_name, value in sorted(get_counters().snapshot().items()):
        lines.append(
            f'modelgovernor_invariant_events_total{{event="{_escape_label(event_name)}"}} {value}'
        )

    return "\n".join(lines) + "\n"


def _escape_label(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')
