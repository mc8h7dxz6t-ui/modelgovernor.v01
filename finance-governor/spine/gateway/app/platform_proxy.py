"""Gateway platform proxy — route to registered platform services."""
from __future__ import annotations

from typing import Any

import httpx

from .config import Settings


def list_platforms_from_sidecar(settings: Settings) -> list[dict[str, Any]]:
    headers = {"x-internal-token": settings.fg_internal_token}
    base = settings.fg_sidecar_url.rstrip("/")
    with httpx.Client(timeout=10.0) as client:
        response = client.get(f"{base}/internal/platforms", headers=headers)
        response.raise_for_status()
        return response.json()


def proxy_platform_request(
    settings: Settings,
    *,
    platform_name: str,
    path: str,
    method: str = "GET",
    json_body: dict[str, Any] | None = None,
    platforms: list[dict[str, Any]] | None = None,
) -> httpx.Response:
    catalog = platforms if platforms is not None else list_platforms_from_sidecar(settings)
    record = next((p for p in catalog if p.get("platform_name") == platform_name), None)
    if record is None:
        raise ValueError(f"platform not registered: {platform_name}")
    if not record.get("enabled", True):
        raise ValueError(f"platform disabled: {platform_name}")
    base_url = (record.get("base_url") or "").rstrip("/")
    if not base_url:
        raise ValueError(f"platform has no base_url: {platform_name}")

    url = f"{base_url}/{path.lstrip('/')}"
    with httpx.Client(timeout=30.0) as client:
        response = getattr(client, method.lower())(url, json=json_body)
    return response
