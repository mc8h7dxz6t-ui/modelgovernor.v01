"""AlgoFreeze proxy API."""
from __future__ import annotations

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from .feed_heartbeat import FeedHeartbeat
from .freeze_controller import FreezeController, FreezeState, VersionRegistry
from .order_gate import OrderGate

app = FastAPI(title="algofreeze", version="0.1.0")

_registry = VersionRegistry(approved_sha="approved-sha-v1")
_controller = FreezeController()
_gate = OrderGate(_controller)
_feed = FeedHeartbeat(max_gap_seconds=2.0)


class OrderRequest(BaseModel):
    order_id: str
    runtime_sha: str
    notional: str = "0"


class VersionUpdate(BaseModel):
    approved_sha: str


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok", "freeze_state": _controller.state.value}


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


@app.post("/orders")
def submit_order(body: OrderRequest) -> dict:
    if not _registry.check(body.runtime_sha):
        _controller.freeze(reason="VERSION_MISMATCH")
        facets = {
            "freeze_state": "FROZEN",
            "deploy_sha": body.runtime_sha,
            "approved_sha": _registry.approved_sha,
        }
        _maybe_crystallize_freeze(body.order_id, facets)
        raise HTTPException(status_code=403, detail="VERSION_MISMATCH: desk frozen")

    if _feed.is_degraded():
        _controller.freeze(reason="FEED_DEGRADED")
        facets = {"freeze_state": "FROZEN", "feed_degraded": True}
        _maybe_crystallize_freeze(body.order_id, facets)
        raise HTTPException(status_code=403, detail="FEED_DEGRADED: desk frozen")

    if not _gate.allow_order():
        raise HTTPException(status_code=403, detail=f"FROZEN: {_controller.reason}")

    return {"status": "ROUTED", "order_id": body.order_id}


def _maybe_crystallize_freeze(operation_id: str, facets: dict) -> None:
    try:
        import os
        from platforms.common.spine_adapter import SpineAdapter

        if os.environ.get("FG_SPINE_ENABLED", "false").lower() != "true":
            return
        adapter = SpineAdapter(platform="algofreeze", spine_enabled=True)
        adapter.crystallize(operation_id=operation_id, risk_tier="critical", facets=facets)
    except Exception:
        pass
