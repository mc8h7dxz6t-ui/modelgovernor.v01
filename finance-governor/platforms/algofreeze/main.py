"""AlgoFreeze proxy API."""
from __future__ import annotations

import logging

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from platforms.common.platform_configs import ALGOFREEZE_CONFIG
from platforms.common.platform_sdk import create_platform_app, increment_invariant
from platforms.common.platform_store import append_platform_event
from platforms.common.spine_helpers import crystallize, crystallize_and_commit

from .feed_heartbeat import FeedHeartbeat
from .freeze_controller import FreezeController, FreezeState, VersionRegistry
from .order_gate import OrderGate

logger = logging.getLogger(__name__)

CONFIG = ALGOFREEZE_CONFIG
_registry = VersionRegistry(approved_sha="approved-sha-v1")
_controller = FreezeController()
_gate = OrderGate(_controller)
_feed = FeedHeartbeat(max_gap_seconds=2.0)
DESK_ID = "desk-default"
FREEZE_POLICY_VERSION = "algofreeze-v1"

app = create_platform_app(
    CONFIG,
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
        "runtime_sha": runtime_sha,
        "desk_id": DESK_ID,
        "deploy_sha": runtime_sha,
        "approved_sha": _registry.approved_sha,
        "freeze_policy_version": FREEZE_POLICY_VERSION,
        "feed_health_vector": {"degraded": _feed.is_degraded()},
    }


@app.get("/events")
def list_events(limit: int = 20) -> list:
    from platforms.common.platform_store import list_platform_events

    return list_platform_events("algofreeze", limit=limit)


@app.post("/orders")
def submit_order(body: OrderRequest) -> dict:
    if not _registry.check(body.runtime_sha):
        _controller.freeze(reason="VERSION_MISMATCH")
        increment_invariant(CONFIG.name, "version_mismatch_freeze_total")
        facets = {**_base_facets(body.runtime_sha), "freeze_state": "FROZEN"}
        append_platform_event("algofreeze", "VERSION_MISMATCH_FREEZE", body.order_id, facets)
        crystallize(CONFIG, body.order_id, facets)
        raise HTTPException(status_code=403, detail="VERSION_MISMATCH: desk frozen")

    if _feed.is_degraded():
        _controller.degrade(reason="FEED_DEGRADED")
        increment_invariant(CONFIG.name, "feed_degraded_total")
        facets = {**_base_facets(body.runtime_sha), "freeze_state": "DEGRADED"}
        append_platform_event("algofreeze", "FEED_DEGRADED", body.order_id, facets)
        crystallize(CONFIG, body.order_id, facets)
        raise HTTPException(status_code=403, detail="FEED_DEGRADED: desk frozen")

    if not _gate.allow_order():
        increment_invariant(CONFIG.name, "frozen_egress_attempt_total")
        append_platform_event("algofreeze", "EGRESS_BLOCKED", body.order_id, {"reason": _controller.reason})
        raise HTTPException(status_code=403, detail=f"FROZEN: {_controller.reason}")

    facets = {**_base_facets(body.runtime_sha), "freeze_state": "ACTIVE", "notional": body.notional}
    crystallize_and_commit(
        CONFIG,
        body.order_id,
        facets,
        committed_exposure=body.notional,
        outcome="routed",
    )
    append_platform_event("algofreeze", "ORDER_ROUTED", body.order_id, facets)
    return {"status": "ROUTED", "order_id": body.order_id}
