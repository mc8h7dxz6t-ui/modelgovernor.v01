"""Subrogation desk evidence ingest — mock desk export connector (production desk = SOW)."""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

import httpx


@dataclass(frozen=True)
class SubroDeskReading:
    vendor: str
    claim_id: str
    total_loss: Decimal
    defendants: dict[str, float]
    salvage_offset: Decimal
    statute_expired: bool
    payload: str
    attestation_hash: str


def attestation_hash(*, vendor: str, payload: str) -> str:
    return hashlib.sha256(f"{vendor}:{payload}".encode()).hexdigest()


def normalize_subro_desk(vendor: str, payload: dict[str, Any]) -> SubroDeskReading:
    graph = payload.get("graph", payload)
    defendants = {str(k): float(v) for k, v in dict(graph.get("defendants") or {}).items()}
    return SubroDeskReading(
        vendor=vendor,
        claim_id=str(graph.get("claim_id", "unknown")),
        total_loss=Decimal(str(graph.get("total_loss", "0"))),
        defendants=defendants,
        salvage_offset=Decimal(str(graph.get("salvage_offset", "0"))),
        statute_expired=bool(graph.get("statute_expired", False)),
        payload=json.dumps(payload, sort_keys=True),
        attestation_hash=attestation_hash(vendor=vendor, payload=json.dumps(payload, sort_keys=True)),
    )


def fetch_subro_desk_feed(vendor: str | None = None) -> SubroDeskReading:
    vendor = vendor or os.environ.get("SUBRO_DESK_VENDOR", "subro-desk-mock")
    url = os.environ.get("SUBRO_DESK_URL")
    if url:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(url)
            response.raise_for_status()
            return normalize_subro_desk(vendor, response.json())
    payload = {
        "graph": {
            "claim_id": "mock-subro-1",
            "total_loss": "100000.00",
            "defendants": {"carrier_a": 0.55, "carrier_b": 0.25},
            "salvage_offset": "5000.00",
            "statute_expired": False,
        }
    }
    return normalize_subro_desk(vendor, payload)


def verify_subro_attestation(*, vendor: str, payload: str, attestation_hash_value: str) -> bool:
    return attestation_hash(vendor=vendor, payload=payload) == attestation_hash_value
