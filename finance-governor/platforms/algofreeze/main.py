"""AlgoFreeze proxy API."""
from __future__ import annotations

import logging
import os

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from platforms.common.platform_metrics import get_platform_counters
from platforms.common.platform_observability import mount_platform_observability
from platforms.common.platform_store import append_platform_event

from .feed_heartbeat import FeedHeartbeat
from .freeze_controller import FreezeController, FreezeState, VersionRegistry
from .order_gate import OrderGate

logger = logging.getLogger(__name__)

app = FastAPI(title="algofreeze", version="0.2.0")

_registry = VersionRegistry(approved_sha="approved-sha-v1")
_controller = FreezeController()
_gate = OrderGate(_controller)
_feed = FeedHeartbeat(max_gap_seconds=2.0)
_COUNTERS = get_platform_counters("algofreeze")
DESK_ID = "desk-default"
FREEZE_POLICY_VERSION = "algofreeze-v1"

mount_platform_observability(
    app,
    platform="algofreeze",
    extra_health=lambda: {"freeze_state": _controller.state.value},
)


class OrderRequest(BaseModel):
    order_id: str
    runtime_sha: str
    notional: str = "0"


class VersionUpdate(BaseModel):
    approved_sha: str


@app.get("/status")
def status() -> dict:
    return {
        "freeze_state": _controller.state.value,
        "reason": _controller.reason,
        "approved_sha": _registry.approved_sha,
        "feed_degraded": _feed.is_degraded(),
        "blocked_egress_attempts": _gate.blocked_attempts,
    }


@app.post("/admin/approved-version")
def set_approved_version(body: VersionUpdate) -> dict:
    global _registry
    _registry = VersionRegistry(approved_sha=body.approved_sha)
    return {"approved_sha": _registry.approved_sha}


@app.post("/admin/feed-packet")
def feed_packet() -> dict:
    _feed.record_packet()
    if _controller.state == FreezeState.DEGRADED:
        _controller.unfreeze()
    return {"ok": True}


def _base_facets(runtime_sha: str) -> dict:
    return {
        "desk_id": DESK_ID,
        "deploy_sha": runtime_sha,
        "approved_sha": _registry.approved_sha,
        "freeze_policy_version": FREEZE_POLICY_VERSION,
        "feed_health_vector": {"degraded": _feed.is_degraded()},
    }


@app.post("/orders")
def submit_order(body: OrderRequest) -> dict:
    if not _registry.check(body.runtime_sha):
        _controller.freeze(reason="VERSION_MISMATCH")
        _COUNTERS.increment("version_mismatch_freeze_total")
        facets = {**_base_facets(body.runtime_sha), "freeze_state": "FROZEN"}
        append_platform_event("algofreeze", "VERSION_MISMATCH_FREEZE", body.order_id, facets)
        _maybe_crystallize(body.order_id, facets)
        raise HTTPException(status_code=403, detail="VERSION_MISMATCH: desk frozen")

    if _feed.is_degraded():
        _controller.degrade(reason="FEED_DEGRADED")
        _COUNTERS.increment("feed_degraded_total")
        facets = {**_base_facets(body.runtime_sha), "freeze_state": "DEGRADED"}
        append_platform_event("algofreeze", "FEED_DEGRADED", body.order_id, facets)
        _maybe_crystallize(body.order_id, facets)
        raise HTTPException(status_code=403, detail="FEED_DEGRADED: desk frozen")

    if not _gate.allow_order():
        _COUNTERS.increment("frozen_egress_attempt_total")
        append_platform_event("algofreeze", "EGRESS_BLOCKED", body.order_id, {"reason": _controller.reason})
        raise HTTPException(status_code=403, detail=f"FROZEN: {_controller.reason}")

    facets = {**_base_facets(body.runtime_sha), "freeze_state": "ACTIVE", "notional": body.notional}
    _maybe_crystallize(body.order_id, facets, commit=True)
    append_platform_event("algofreeze", "ORDER_ROUTED", body.order_id, facets)
    return {"status": "ROUTED", "order_id": body.order_id}


def _maybe_crystallize(operation_id: str, facets: dict, *, commit: bool = False) -> None:
    if os.environ.get("FG_SPINE_ENABLED", "false").lower() != "true":
        return
    try:
        from platforms.common.spine_adapter import CommitOutcome, SpineAdapter

        adapter = SpineAdapter(platform="algofreeze", spine_enabled=True)
        crystal = adapter.crystallize(operation_id=operation_id, risk_tier="critical", facets=facets)
        if commit:
            adapter.commit(
                CommitOutcome(
                    operation_id=operation_id,
                    crystal_id=crystal.crystal_id,
                    facets=facets,
                    outcome="routed",
                    committed_exposure=facets.get("notional", "0"),
                )
            )
    except Exception as exc:
        logger.warning("spine crystallize failed operation=%s: %s", operation_id, exc)
