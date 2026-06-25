"""Production inference rail — HTTP provider with circuit breaker and mock fallback."""
from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

import httpx

from .mock_rail import RailOutcome, score_application as mock_score

logger = logging.getLogger(__name__)


class RailCircuitOpenError(RuntimeError):
    pass


class RailProviderError(RuntimeError):
    pass


@dataclass
class RailConfig:
    mode: str = "mock"
    url: str = ""
    timeout_s: float = 10.0
    circuit_threshold: int = 5
    api_key_header: str = "x-api-key"
    api_key: str = ""

    @classmethod
    def from_env(cls) -> RailConfig:
        return cls(
            mode=os.environ.get("FG_CREDIT_RAIL_MODE", "mock").lower(),
            url=os.environ.get("FG_CREDIT_RAIL_URL", "").rstrip("/"),
            timeout_s=float(os.environ.get("FG_CREDIT_RAIL_TIMEOUT", "10")),
            circuit_threshold=int(os.environ.get("FG_CREDIT_RAIL_CIRCUIT_THRESHOLD", "5")),
            api_key_header=os.environ.get("FG_CREDIT_RAIL_API_KEY_HEADER", "x-api-key"),
            api_key=os.environ.get("FG_CREDIT_RAIL_API_KEY", ""),
        )


class InferenceRailClient:
    """Routes credit scoring to live HTTP rail or mock; auto mode fails over to mock."""

    def __init__(self, config: RailConfig | None = None) -> None:
        self.config = config or RailConfig.from_env()
        self._consecutive_failures = 0
        self._circuit_open = False
        self._circuit_opened_at: float | None = None
        self._circuit_reset_s = float(os.environ.get("FG_CREDIT_RAIL_CIRCUIT_RESET_S", "30"))

    @property
    def circuit_open(self) -> bool:
        if self._circuit_open and self._circuit_opened_at is not None:
            if time.monotonic() - self._circuit_opened_at >= self._circuit_reset_s:
                self._circuit_open = False
                self._consecutive_failures = 0
                self._circuit_opened_at = None
        return self._circuit_open

    def score(
        self,
        *,
        application_id: str,
        exposure: Decimal,
        model_version_id: str,
        features: dict[str, Any] | None = None,
    ) -> RailOutcome:
        mode = self.config.mode
        if mode == "mock":
            return mock_score(exposure=exposure, model_version_id=model_version_id)

        if self.circuit_open:
            if mode == "auto":
                logger.warning("credit rail circuit open — auto fallback to mock application=%s", application_id)
                return mock_score(exposure=exposure, model_version_id=model_version_id)
            raise RailCircuitOpenError("inference rail circuit open")

        if not self.config.url:
            if mode == "auto":
                return mock_score(exposure=exposure, model_version_id=model_version_id)
            raise RailProviderError("FG_CREDIT_RAIL_URL not configured")

        try:
            outcome = self._http_score(
                application_id=application_id,
                exposure=exposure,
                model_version_id=model_version_id,
                features=features or {},
            )
            self._consecutive_failures = 0
            return outcome
        except Exception as exc:
            self._consecutive_failures += 1
            logger.warning(
                "credit rail failure %s/%s application=%s: %s",
                self._consecutive_failures,
                self.config.circuit_threshold,
                application_id,
                exc,
            )
            if self._consecutive_failures >= self.config.circuit_threshold:
                self._circuit_open = True
                self._circuit_opened_at = time.monotonic()
            if mode == "auto":
                return mock_score(exposure=exposure, model_version_id=model_version_id)
            raise RailProviderError(str(exc)) from exc

    def _http_score(
        self,
        *,
        application_id: str,
        exposure: Decimal,
        model_version_id: str,
        features: dict[str, Any],
    ) -> RailOutcome:
        headers = {"content-type": "application/json"}
        if self.config.api_key:
            headers[self.config.api_key_header] = self.config.api_key
        payload = {
            "application_id": application_id,
            "exposure_amount": str(exposure),
            "model_version_id": model_version_id,
            "features": features,
        }
        started = time.perf_counter()
        with httpx.Client(timeout=self.config.timeout_s) as client:
            response = client.post(f"{self.config.url}/v1/score", headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
        latency_ms = int((time.perf_counter() - started) * 1000)
        return RailOutcome(
            decision=str(data.get("decision", "REFER")).upper(),
            score=float(data.get("score", 0.0)),
            explanation_id=str(data.get("explanation_id", "exp-live-rail")),
            latency_ms=latency_ms,
        )


_default_client: InferenceRailClient | None = None


def get_inference_rail() -> InferenceRailClient:
    global _default_client
    if _default_client is None:
        _default_client = InferenceRailClient()
    return _default_client


def reset_inference_rail() -> None:
    global _default_client
    _default_client = None
