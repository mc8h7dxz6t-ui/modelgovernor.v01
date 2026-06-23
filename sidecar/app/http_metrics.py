"""Prometheus RED metrics for HTTP handlers."""
from __future__ import annotations

import time
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

try:
    from prometheus_client import Counter, Histogram

    HTTP_REQUESTS = Counter(
        "modelgovernor_http_requests_total",
        "HTTP requests processed by the sidecar.",
        ["method", "route", "status"],
    )
    HTTP_LATENCY = Histogram(
        "modelgovernor_http_request_duration_seconds",
        "HTTP request latency in seconds.",
        ["method", "route"],
        buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
    )
    _METRICS_ENABLED = True
except ImportError:
    _METRICS_ENABLED = False


def _route_label(request: Request) -> str:
    route = request.scope.get("route")
    if route is not None and getattr(route, "path", None):
        return str(route.path)
    return request.url.path


class PrometheusMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if not _METRICS_ENABLED:
            return await call_next(request)

        method = request.method
        route = _route_label(request)
        start = time.perf_counter()
        status_code = "500"
        try:
            response = await call_next(request)
            status_code = str(response.status_code)
            return response
        finally:
            elapsed = time.perf_counter() - start
            HTTP_LATENCY.labels(method=method, route=route).observe(elapsed)
            HTTP_REQUESTS.labels(method=method, route=route, status=status_code).inc()
