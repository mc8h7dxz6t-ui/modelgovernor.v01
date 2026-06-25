"""External oracle feed adapters — HTTP/API sources for parametric triggers."""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

import httpx


@dataclass(frozen=True)
class OracleReading:
    source: str
    metric_value: Decimal
    threshold: Decimal
    payload: str
    attestation_hash: str
    fetched_at: str


def attestation_hash(*, source: str, payload: str) -> str:
    return hashlib.sha256(f"{source}:{payload}".encode()).hexdigest()


def fetch_usgs_earthquake_mock() -> OracleReading:
    """Deterministic mock USGS-style feed for demos."""
    payload = json.dumps({"magnitude": 7.2, "place": "Mock Epicenter", "type": "earthquake"})
    return OracleReading(
        source="usgs-feed",
        metric_value=Decimal("7.2"),
        threshold=Decimal("6.5"),
        payload=payload,
        attestation_hash=attestation_hash(source="usgs-feed", payload=payload),
        fetched_at="demo",
    )


def fetch_oracle_feed(source: str | None = None) -> OracleReading:
    source = source or os.environ.get("ORACLE_FEED_SOURCE", "usgs-feed")
    url = os.environ.get("ORACLE_FEED_URL")

    if url:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(url)
            response.raise_for_status()
            data = response.json()
        metric = Decimal(str(data.get("magnitude", data.get("metric_value", "0"))))
        threshold = Decimal(str(data.get("threshold", "6.5")))
        payload = json.dumps(data, sort_keys=True)
        return OracleReading(
            source=source,
            metric_value=metric,
            threshold=threshold,
            payload=payload,
            attestation_hash=attestation_hash(source=source, payload=payload),
            fetched_at=str(data.get("time", "live")),
        )

    if source == "usgs-feed":
        return fetch_usgs_earthquake_mock()
    raise ValueError(f"unsupported oracle source: {source}")
