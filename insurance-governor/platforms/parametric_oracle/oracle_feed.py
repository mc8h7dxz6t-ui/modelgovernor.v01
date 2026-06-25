"""External oracle feed adapters — HTTP/API sources for parametric triggers."""
from __future__ import annotations

import json
import os
from decimal import Decimal

import httpx

from platforms.common.integrations.oracle_providers import oracle_feed_mode, resolve_live_feed
from platforms.common.integrations.oracle_types import OracleReading, attestation_hash

# Re-export for backward compatibility
__all__ = ["OracleReading", "attestation_hash", "fetch_oracle_feed", "fetch_usgs_earthquake_mock"]


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
    mode = oracle_feed_mode()

    if mode == "live":
        return resolve_live_feed(source)

    url = os.environ.get("ORACLE_FEED_URL")
    if url:
        with httpx.Client(timeout=10.0) as client:
            headers = {"accept": "application/json"}
            api_key = os.environ.get("ORACLE_FEED_API_KEY")
            if api_key:
                headers["authorization"] = f"Bearer {api_key}"
            response = client.get(url, headers=headers)
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

    if source in ("usgs-feed", "usgs"):
        return fetch_usgs_earthquake_mock()
    raise ValueError(f"unsupported oracle source: {source} (set ORACLE_FEED_MODE=live or ORACLE_FEED_URL)")
