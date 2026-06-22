"""
Prometheus metrics definitions for the policy sidecar.

A module-scoped CollectorRegistry is used so that test environments that
re-import app modules (e.g. test_scaffold_smoke) do not collide with the
global prometheus_client registry.

All counters use explicit label sets so that dashboards and alerts can be
built against stable metric names without any post-hoc string parsing.
"""
from prometheus_client import CollectorRegistry, Counter

registry = CollectorRegistry()

# Reserve path
reserve_requests_total = Counter(
    "sidecar_reserve_requests_total",
    "Total reserve requests handled by the sidecar, labelled by outcome.",
    ["outcome"],  # accepted | replayed | rejected | error
    registry=registry,
)

reserve_amount_total = Counter(
    "sidecar_reserve_amount_dollars_total",
    "Cumulative dollar amount reserved by accepted (non-replay) reserve calls.",
    registry=registry,
)

# Settle path
settle_requests_total = Counter(
    "sidecar_settle_requests_total",
    "Total settle requests handled by the sidecar, labelled by outcome.",
    ["outcome"],  # settled | replayed | rejected | error
    registry=registry,
)

settle_amount_total = Counter(
    "sidecar_settle_amount_dollars_total",
    "Cumulative dollar amount recorded on accepted (non-replay) settle calls.",
    registry=registry,
)
