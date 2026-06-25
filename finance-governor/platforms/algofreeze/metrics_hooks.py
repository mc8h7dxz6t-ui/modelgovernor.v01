"""AlgoFreeze invariant hooks."""
from __future__ import annotations

from time import monotonic

from platforms.common.event_store import AppendOnlyEventStore
from platforms.common.mesh_guard import get_mesh_guard
from platforms.common.platform_metrics import get_platform_metrics

from .freeze_controller import FreezeController, FreezeState

_events = AppendOnlyEventStore()


def get_event_store() -> AppendOnlyEventStore:
    return _events


def record_freeze(
    controller: FreezeController,
    *,
    reason: str,
    operation_id: str,
    runtime_sha: str | None = None,
    approved_sha: str | None = None,
    started_at: float | None = None,
) -> None:
    controller.freeze(reason)
    mesh = get_mesh_guard()
    mesh.set_algo_frozen(reason)
    metrics = get_platform_metrics()
    if reason == "VERSION_MISMATCH":
        metrics.increment("version_mismatch_freeze_total")
    if reason == "FEED_DEGRADED":
        metrics.increment("feed_degraded_total")
    if started_at is not None:
        latency_ms = int((monotonic() - started_at) * 1000)
        metrics.observe("freeze_activation_latency_ms", latency_ms)
    _events.append(
        platform="algofreeze",
        event_type="FREEZE",
        operation_id=operation_id,
        payload={
            "reason": reason,
            "runtime_sha": runtime_sha,
            "approved_sha": approved_sha,
            "state": FreezeState.FROZEN.value,
        },
    )


def record_blocked_egress(operation_id: str, reason: str) -> None:
    get_platform_metrics().increment("frozen_egress_attempt_total")
    _events.append(
        platform="algofreeze",
        event_type="EGRESS_BLOCKED",
        operation_id=operation_id,
        payload={"reason": reason},
    )


def record_unfreeze(controller: FreezeController) -> None:
    controller.unfreeze()
    get_mesh_guard().set_algo_active()
    _events.append(
        platform="algofreeze",
        event_type="UNFREEZE",
        operation_id="admin",
        payload={"state": FreezeState.ACTIVE.value},
    )
