"""Live oracle / meteorological feed providers."""
from __future__ import annotations

import hashlib
import json
import os
from decimal import Decimal
from typing import Any

import httpx

from platforms.common.integrations.oracle_types import OracleReading, attestation_hash


def oracle_feed_mode() -> str:
    return os.environ.get("ORACLE_FEED_MODE", "mock").lower()


def _auth_headers() -> dict[str, str]:
    headers = {"accept": "application/json"}
    key = os.environ.get("ORACLE_FEED_API_KEY") or os.environ.get("CHAINLINK_API_KEY")
    if key:
        headers["authorization"] = f"Bearer {key}"
    return headers


def fetch_usgs_live() -> OracleReading:
    """USGS GeoJSON earthquake feed (public, no key)."""
    url = os.environ.get(
        "USGS_FEED_URL",
        "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/2.5_day.geojson",
    )
    with httpx.Client(timeout=15.0) as client:
        response = client.get(url, headers=_auth_headers())
        response.raise_for_status()
        data = response.json()
    features = data.get("features", [])
    if not features:
        raise ValueError("USGS feed returned no features")
    props = features[0].get("properties", {})
    magnitude = Decimal(str(props.get("mag", "0")))
    threshold = Decimal(os.environ.get("ORACLE_MAGNITUDE_THRESHOLD", "6.5"))
    payload = json.dumps(props, sort_keys=True)
    return OracleReading(
        source="usgs-live",
        metric_value=magnitude,
        threshold=threshold,
        payload=payload,
        attestation_hash=attestation_hash(source="usgs-live", payload=payload),
        fetched_at=str(props.get("time", "live")),
    )


def fetch_noaa_weather() -> OracleReading:
    """NOAA National Weather Service — authenticated point forecast."""
    url = os.environ.get("NOAA_API_URL")
    if not url:
        raise RuntimeError("NOAA_API_URL required for noaa-weather source")
    with httpx.Client(timeout=15.0) as client:
        response = client.get(url, headers={**_auth_headers(), "User-Agent": "InsuranceGovernor/1.0"})
        response.raise_for_status()
        data = response.json()
    metric = Decimal(str(data.get("windSpeed", data.get("metric_value", "0"))))
    threshold = Decimal(str(data.get("threshold", os.environ.get("ORACLE_WIND_THRESHOLD", "75"))))
    payload = json.dumps(data, sort_keys=True)
    source = "noaa-weather"
    return OracleReading(
        source=source,
        metric_value=metric,
        threshold=threshold,
        payload=payload,
        attestation_hash=attestation_hash(source=source, payload=payload),
        fetched_at=str(data.get("timestamp", "live")),
    )


def fetch_chainlink_aggregator() -> OracleReading:
    """Chainlink-style HTTP aggregator feed."""
    url = os.environ.get("CHAINLINK_FEED_URL") or os.environ.get("ORACLE_FEED_URL")
    if not url:
        raise RuntimeError("CHAINLINK_FEED_URL required for chainlink source")
    with httpx.Client(timeout=15.0) as client:
        response = client.get(url, headers=_auth_headers())
        response.raise_for_status()
        data = response.json()
    answer = data.get("answer", data.get("result", data))
    if isinstance(answer, dict):
        metric = Decimal(str(answer.get("value", answer.get("metric_value", "0"))))
    else:
        metric = Decimal(str(answer))
    threshold = Decimal(str(data.get("threshold", os.environ.get("ORACLE_DEFAULT_THRESHOLD", "1"))))
    payload = json.dumps(data, sort_keys=True)
    source = "chainlink"
    return OracleReading(
        source=source,
        metric_value=metric,
        threshold=threshold,
        payload=payload,
        attestation_hash=attestation_hash(source=source, payload=payload),
        fetched_at=str(data.get("updatedAt", "live")),
    )


def fetch_custom_http_feed(url: str, source: str) -> OracleReading:
    with httpx.Client(timeout=15.0) as client:
        response = client.get(url, headers=_auth_headers())
        response.raise_for_status()
        data = response.json()
    metric = Decimal(str(data.get("magnitude", data.get("metric_value", data.get("value", "0")))))
    threshold = Decimal(str(data.get("threshold", "6.5")))
    payload = json.dumps(data, sort_keys=True)
    return OracleReading(
        source=source,
        metric_value=metric,
        threshold=threshold,
        payload=payload,
        attestation_hash=attestation_hash(source=source, payload=payload),
        fetched_at=str(data.get("time", data.get("updatedAt", "live"))),
    )


def resolve_live_feed(source: str) -> OracleReading:
    if source in ("usgs-live", "usgs"):
        return fetch_usgs_live()
    if source in ("noaa-weather", "noaa"):
        return fetch_noaa_weather()
    if source in ("chainlink", "chainlink-aggregator"):
        return fetch_chainlink_aggregator()
    url = os.environ.get("ORACLE_FEED_URL")
    if url:
        return fetch_custom_http_feed(url, source)
    raise ValueError(f"unsupported live oracle source: {source}")
