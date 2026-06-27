"""Shared health, readiness, and metrics endpoints for platforms."""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import PlainTextResponse

from .platform_metrics import get_platform_counters, render_prometheus_text


def mount_platform_observability(
    app: FastAPI,
    *,
    platform: str,
    ready_check: Callable[[], bool] | None = None,
    extra_health: Callable[[], dict[str, Any]] | None = None,
) -> None:
    @app.get("/healthz")
    def healthz() -> dict:
        body: dict[str, Any] = {"status": "ok", "platform": platform}
        if extra_health:
            body.update(extra_health())
        return body

    @app.get("/readyz")
    def readyz() -> dict:
        if ready_check is not None and not ready_check():
            raise HTTPException(status_code=503, detail="not ready")
        return {"status": "ready", "platform": platform}

    @app.get("/metrics", response_class=PlainTextResponse)
    def metrics() -> str:
        try:
            from prometheus_client import generate_latest

            return generate_latest().decode("utf-8")
        except ImportError:
            return render_prometheus_text(platform)
