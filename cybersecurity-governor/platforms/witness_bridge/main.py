"""WitnessBridge — IdP, cloud audit, and generic witness ingest."""
from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel, Field

from platforms.common.integrations.telemetry import normalize_event
from platforms.common.platform_sdk import GovernedPlatform, spine_health_payload
from .silence_detector import WitnessState

app = FastAPI(title="witness-bridge", version="0.1.0")
_GOVERNED = GovernedPlatform("witness_bridge")
_witness = WitnessState()


class IngestResponse(BaseModel):
    accepted: bool
    source: str
    event_type: str
    severity: str
    crystal_id: str | None = None
    silent_sources: list[str] = Field(default_factory=list)


def _is_erasure_action(action: str) -> bool:
    lowered = action.lower()
    return any(token in lowered for token in ("delete", "stoplogging", "eras", "clear"))


@app.get("/healthz")
def healthz() -> dict:
    return spine_health_payload("witness_bridge")


@app.get("/readyz")
def readyz() -> dict:
    return healthz()


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
        "witness_decision": "WITNESSED",
        **event.facets,
    }
    crystal_id = None
    if event.severity == "critical" or _is_erasure_action(event.action):
        crystal_id = _GOVERNED.govern_operation(
            operation_id,
            facets,
            decision="WITNESSED",
            reserve_amount="0",
            outcome="witnessed",
        )
    return IngestResponse(
        accepted=True,
        source=event.source,
        event_type=event.event_type,
        severity=event.severity,
        crystal_id=crystal_id,
        silent_sources=_witness.silent_sources(),
    )
