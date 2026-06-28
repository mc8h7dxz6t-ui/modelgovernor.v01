"""FNOL write-back adapters — governed decision sync to core PAS (read/write stub)."""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import httpx


@dataclass(frozen=True)
class WritebackResult:
    vendor: str
    claim_id: str
    status: str
    external_ref: str | None = None
    dry_run: bool = True


def writeback_enabled() -> bool:
    return os.environ.get("FNOL_WRITEBACK_MODE", "dry_run").lower() == "live"


def writeback_guidewire(*, claim_id: str, decision: str, facets: dict[str, Any]) -> WritebackResult:
    url = os.environ.get("GUIDEWIRE_WRITEBACK_URL")
    if not writeback_enabled() or not url:
        return WritebackResult("guidewire", claim_id, "dry_run_recorded", f"dry-{claim_id}", dry_run=True)
    body = {"claimNumber": claim_id, "gateDecision": decision, "facets": facets}
    headers = {"content-type": "application/json"}
    token = os.environ.get("GUIDEWIRE_API_TOKEN")
    if token:
        headers["authorization"] = f"Bearer {token}"
    with httpx.Client(timeout=15.0) as client:
        response = client.post(url, json=body, headers=headers)
        response.raise_for_status()
        data = response.json()
    return WritebackResult("guidewire", claim_id, "synced", str(data.get("id", claim_id)), dry_run=False)


def writeback_ice(*, claim_id: str, decision: str, facets: dict[str, Any]) -> WritebackResult:
    url = os.environ.get("ICE_WRITEBACK_URL")
    if not writeback_enabled() or not url:
        return WritebackResult("ice", claim_id, "dry_run_recorded", f"dry-{claim_id}", dry_run=True)
    body = {"claimReference": claim_id, "governedDecision": decision, "facets": facets}
    headers = {"content-type": "application/json"}
    token = os.environ.get("ICE_API_TOKEN")
    if token:
        headers["authorization"] = f"Bearer {token}"
    with httpx.Client(timeout=15.0) as client:
        response = client.post(url, json=body, headers=headers)
        response.raise_for_status()
        data = response.json()
    return WritebackResult("ice", claim_id, "synced", str(data.get("syncId", claim_id)), dry_run=False)


def writeback_snapsheet(*, claim_id: str, decision: str, facets: dict[str, Any]) -> WritebackResult:
    url = os.environ.get("SNAPSHEET_WRITEBACK_URL")
    if not writeback_enabled() or not url:
        return WritebackResult("snapsheet", claim_id, "dry_run_recorded", f"dry-{claim_id}", dry_run=True)
    body = {"claimNumber": claim_id, "gateDecision": decision, "facets": facets}
    headers = {"content-type": "application/json"}
    token = os.environ.get("SNAPSHEET_API_TOKEN")
    if token:
        headers["authorization"] = f"Bearer {token}"
    with httpx.Client(timeout=15.0) as client:
        response = client.post(url, json=body, headers=headers)
        response.raise_for_status()
        data = response.json()
    return WritebackResult("snapsheet", claim_id, "synced", str(data.get("id", claim_id)), dry_run=False)


def writeback_acturis(*, claim_id: str, decision: str, facets: dict[str, Any]) -> WritebackResult:
    url = os.environ.get("ACTURIS_WRITEBACK_URL")
    if not writeback_enabled() or not url:
        return WritebackResult("acturis", claim_id, "dry_run_recorded", f"dry-{claim_id}", dry_run=True)
    body = {"claimReference": claim_id, "governedDecision": decision, "metadata": facets}
    with httpx.Client(timeout=15.0) as client:
        response = client.post(url, json=body)
        response.raise_for_status()
        data = response.json()
    return WritebackResult("acturis", claim_id, "synced", str(data.get("notificationId", claim_id)), dry_run=False)


_WRITEBACK = {
    "guidewire": writeback_guidewire,
    "snapsheet": writeback_snapsheet,
    "acturis": writeback_acturis,
    "ice": writeback_ice,
}


def sync_fnol_decision(*, vendor: str, claim_id: str, decision: str, facets: dict[str, Any]) -> WritebackResult:
    adapter = _WRITEBACK.get(vendor.lower())
    if adapter is None:
        return WritebackResult(vendor, claim_id, "unsupported_vendor", dry_run=True)
    return adapter(claim_id=claim_id, decision=decision, facets=facets)
