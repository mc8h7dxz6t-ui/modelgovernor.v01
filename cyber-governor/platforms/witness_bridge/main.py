"""WitnessBridge — universal webhook ingest for IdP, cloud audit, SIEM, generic."""
from __future__ import annotations

import os
from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel, Field

from platforms.common.integrations import normalize_event
from .silence_detector import WitnessState

app = FastAPI(title="witness-bridge", version="0.1.0")
_witness = WitnessState()


class IngestResponse(BaseModel):
    accepted: bool
    source: str
    event_type: str
    severity: str
    crystal_id: str | None = None
    silent_sources: list[str] = Field(default_factory=list)


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok", "silent_sources": _witness.silent_sources()}


@app.post("/ingest/{source}", response_model=IngestResponse)
def ingest(source: str, payload: dict[str, Any]) -> IngestResponse:
    event = normalize_event(source, payload)
    _witness.record(event.source)
    operation_id = f"{event.source}-{event.raw_ref or event.event_type}"
    facets = {
        "source": event.source,
        "event_type": event.event_type,
        "principal_id": event.principal_id,
        "resource_id": event.resource_id,
        "action": event.action,
        "severity": event.severity,
        **event.facets,
    }
    crystal_id = None
    if event.severity == "critical" or _is_erasure_action(event.action):
        crystal_id = _crystallize_if_spine(operation_id, facets, critical=True)
    return IngestResponse(
        accepted=True,
        source=event.source,
        event_type=event.event_type,
        severity=event.severity,
        crystal_id=crystal_id,
        silent_sources=_witness.silent_sources(),
    )


def _is_erasure_action(action: str) -> bool:
    lowered = action.lower()
    return any(token in lowered for token in ("delete", "stoplogging", "eras", "clear"))


def _crystallize_if_spine(operation_id: str, facets: dict, *, critical: bool) -> str | None:
    if os.environ.get("CG_SPINE_ENABLED", "false").lower() != "true":
        return None
    try:
        from platforms.common.spine_adapter import CommitOutcome, SpineAdapter

        adapter = SpineAdapter(platform="witness_bridge", spine_enabled=True)
        crystal = adapter.crystallize(
            operation_id=operation_id,
            risk_tier="critical" if critical else "standard",
            facets=facets,
            policy_id="witness-standard-us",
            account_id="tenant-default",
        )
        if critical:
            adapter.commit(
                CommitOutcome(
                    operation_id=operation_id,
                    crystal_id=crystal.crystal_id,
                    facets=facets,
                    outcome="witnessed",
                )
            )
        return crystal.crystal_id
    except Exception:
        return None
