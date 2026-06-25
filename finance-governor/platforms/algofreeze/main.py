"""AlgoFreeze proxy API — version/feed-aware kill switch."""
from __future__ import annotations

from time import monotonic

from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel

from platforms.common.mesh_guard import get_mesh_guard

from .deploy_registry import DeployRegistry
from .feed_heartbeat import FeedHeartbeat
from .freeze_controller import FreezeController, FreezeState
from .metrics_hooks import (
    get_event_store,
    record_blocked_egress,
    record_freeze,
    record_unfreeze,
)
from .order_gate import OrderGate
from platforms.common.platform_metrics import get_platform_metrics

app = FastAPI(title="algofreeze", version="0.2.0")

_registry = DeployRegistry()
_registry.register_approval("approved-sha-v1", approved_by="bootstrap", ci_pipeline_id="init")
_controller = FreezeController()
_gate = OrderGate(_controller)
_feed = FeedHeartbeat(max_gap_seconds=2.0)


class OrderRequest(BaseModel):
    order_id: str
    runtime_sha: str
    notional: str = "0"
    desk_id: str = "desk-default"


class DeployApproval(BaseModel):
    sha: str
    approved_by: str = "ci-pipeline"
    ci_pipeline_id: str = "manual"


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok", "freeze_state": _controller.state.value}


@app.get("/readyz")
def readyz() -> dict:
    return {"ready": True, "approved_sha": _registry.approved_sha}


@app.get("/metrics")
def metrics() -> Response:
    return Response(content=get_platform_metrics().prometheus_text(), media_type="text/plain")


@app.get("/status")
def status() -> dict:
    mesh = get_mesh_guard()
    return {
        "freeze_state": _controller.state.value,
        "reason": _controller.reason,
        "approved_sha": _registry.approved_sha,
        "feed_degraded": _feed.is_degraded(),
        "blocked_egress_attempts": _gate.blocked_attempts,
        "mesh_algo_state": mesh.algo_state.value,
        "deploy_history_count": len(_registry.history()),
    }


@app.get("/admin/deploy-registry")
def deploy_registry_history() -> dict:
    return {
        "approved_sha": _registry.approved_sha,
        "history": [
            {
                "sha": r.sha,
                "approved_by": r.approved_by,
                "approved_at": r.approved_at,
                "ci_pipeline_id": r.ci_pipeline_id,
                "environment": r.environment,
            }
            for r in _registry.history()
        ],
    }


@app.post("/admin/deploy-registry")
def approve_deploy(body: DeployApproval) -> dict:
    record = _registry.register_approval(
        body.sha, approved_by=body.approved_by, ci_pipeline_id=body.ci_pipeline_id
    )
    if _controller.state == FreezeState.FROZEN and _controller.reason == "VERSION_MISMATCH":
        record_unfreeze(_controller)
    return {
        "approved_sha": record.sha,
        "approved_at": record.approved_at,
        "ci_pipeline_id": record.ci_pipeline_id,
    }


@app.post("/admin/feed-packet")
def feed_packet() -> dict:
    _feed.record_packet()
    if _controller.state == FreezeState.DEGRADED:
        record_unfreeze(_controller)
    return {"ok": True}


@app.post("/admin/unfreeze")
def admin_unfreeze() -> dict:
    record_unfreeze(_controller)
    return {"freeze_state": _controller.state.value}


@app.get("/internal/events/recent")
def recent_events(limit: int = 20) -> dict:
    events = get_event_store().recent(limit)
    return {
        "events": [
            {
                "seq": e.seq,
                "event_type": e.event_type,
                "operation_id": e.operation_id,
                "payload": e.payload,
                "event_hash": e.event_hash,
            }
            for e in events
        ],
        "chain_valid": get_event_store().verify_chain(),
    }


@app.post("/orders")
def submit_order(body: OrderRequest) -> dict:
    started = monotonic()
    ok, mismatch_reason = _registry.check_runtime(body.runtime_sha)
    if not ok:
        record_freeze(
            _controller,
            reason=mismatch_reason or "VERSION_MISMATCH",
            operation_id=body.order_id,
            runtime_sha=body.runtime_sha,
            approved_sha=_registry.approved_sha,
            started_at=started,
        )
        facets = {
            "freeze_state": "FROZEN",
            "deploy_sha": body.runtime_sha,
            "approved_sha": _registry.approved_sha,
            "ci_registry": True,
        }
        _maybe_crystallize_freeze(body.order_id, facets)
        raise HTTPException(status_code=403, detail=f"{mismatch_reason}: desk frozen")

    if _feed.is_degraded():
        record_freeze(
            _controller,
            reason="FEED_DEGRADED",
            operation_id=body.order_id,
            started_at=started,
        )
        facets = {"freeze_state": "FROZEN", "feed_degraded": True}
        _maybe_crystallize_freeze(body.order_id, facets)
        raise HTTPException(status_code=403, detail="FEED_DEGRADED: desk frozen")

    if not _gate.allow_order():
        record_blocked_egress(body.order_id, _controller.reason or "FROZEN")
        raise HTTPException(status_code=403, detail=f"FROZEN: {_controller.reason}")

    get_event_store().append(
        platform="algofreeze",
        event_type="ORDER_ROUTED",
        operation_id=body.order_id,
        payload={"runtime_sha": body.runtime_sha, "notional": body.notional},
    )
    return {"status": "ROUTED", "order_id": body.order_id, "approved_sha": _registry.approved_sha}


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
