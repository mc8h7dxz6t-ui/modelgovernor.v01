"""Shared reserve → provider → settle flow for gateway entrypoints."""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

import httpx
from fastapi import HTTPException

from .config import Settings
from .providers.router import get_provider_router

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class GovernedDispatchOutcome:
    idempotency_key: str
    reserve_status: str
    settle_status: str
    actual_cost: Decimal
    provider_request_id: str
    provider_name: str
    model: str
    response_text: str
    input_tokens: int
    output_tokens: int
    latency_ms: int


def execute_governed_dispatch(
    *,
    settings: Settings,
    user_id: str,
    trace_id: str,
    model: str,
    estimated_cost: Decimal,
    idempotency_key: str | None,
    prompt: str | None,
    messages: list[dict[str, Any]] | None,
    auth_subject: str,
) -> GovernedDispatchOutcome:
    op_key = idempotency_key or f"gw-{uuid.uuid4().hex[:16]}"
    headers = {
        "x-internal-token": settings.sidecar_internal_token,
        "content-type": "application/json",
    }
    reserve_payload = {
        "user_id": user_id,
        "trace_id": trace_id,
        "idempotency_key": op_key,
        "model": model,
        "estimated_cost": str(estimated_cost),
    }

    with httpx.Client(timeout=settings.provider_timeout_seconds + 5.0) as client:
        reserve = client.post(
            f"{settings.sidecar_url.rstrip('/')}/reserve",
            headers=headers,
            json=reserve_payload,
        )
        if reserve.status_code >= 400:
            raise HTTPException(status_code=reserve.status_code, detail=reserve.text)
        reserve_body = reserve.json()

        provider_result = get_provider_router().dispatch(
            settings=settings,
            model=model,
            prompt=prompt,
            messages=messages,
        )
        actual_cost = min(provider_result.actual_cost, estimated_cost)

        settle_payload = {
            "idempotency_key": op_key,
            "outcome": "SETTLED",
            "actual_cost": str(actual_cost),
            "provider_request_id": provider_result.provider_request_id,
            "provider_name": provider_result.provider_name,
            "model": provider_result.model,
            "input_tokens": provider_result.input_tokens,
            "output_tokens": provider_result.output_tokens,
            "cached_input_tokens": provider_result.cached_input_tokens,
            "cached_output_tokens": provider_result.cached_output_tokens,
            "latency_ms": provider_result.latency_ms,
        }
        settle = client.post(
            f"{settings.sidecar_url.rstrip('/')}/settle",
            headers=headers,
            json=settle_payload,
        )
        if settle.status_code >= 400:
            raise HTTPException(status_code=settle.status_code, detail=settle.text)
        settle_body = settle.json()

    logger.info(
        "governed dispatch subject=%s provider=%s model=%s idempotency_key=%s cost=%s",
        auth_subject,
        provider_result.provider_name,
        provider_result.model,
        op_key,
        actual_cost,
    )
    return GovernedDispatchOutcome(
        idempotency_key=op_key,
        reserve_status=reserve_body["status"],
        settle_status=settle_body["status"],
        actual_cost=actual_cost,
        provider_request_id=provider_result.provider_request_id,
        provider_name=provider_result.provider_name,
        model=provider_result.model,
        response_text=provider_result.response_text,
        input_tokens=provider_result.input_tokens,
        output_tokens=provider_result.output_tokens,
        latency_ms=provider_result.latency_ms,
    )
