"""Anthropic provider router."""
from __future__ import annotations

import time
import uuid

from fastapi import HTTPException

from ..config import Settings
from ..pricing import compute_token_cost
from .base import ProviderDispatchResult


class AnthropicProvider:
    def dispatch(
        self,
        *,
        settings: Settings,
        model: str,
        prompt: str | None,
        messages: list[dict[str, str]] | None,
    ) -> ProviderDispatchResult:
        if not settings.anthropic_api_key:
            raise HTTPException(status_code=503, detail="ANTHROPIC_API_KEY is not configured")

        from anthropic import Anthropic

        model_name = model.split("/")[-1]
        started = time.monotonic()
        client = Anthropic(api_key=settings.anthropic_api_key, timeout=settings.provider_timeout_seconds)
        if messages:
            response = client.messages.create(
                model=model_name,
                max_tokens=settings.provider_max_output_tokens,
                messages=messages,
            )
        else:
            response = client.messages.create(
                model=model_name,
                max_tokens=settings.provider_max_output_tokens,
                messages=[{"role": "user", "content": prompt or ""}],
            )
        latency_ms = int((time.monotonic() - started) * 1000)
        input_tokens = int(response.usage.input_tokens)
        output_tokens = int(response.usage.output_tokens)
        response_text = "".join(
            block.text for block in response.content if getattr(block, "type", "") == "text"
        )
        return ProviderDispatchResult(
            provider_request_id=response.id or f"anthropic-{uuid.uuid4().hex[:16]}",
            provider_name="anthropic",
            model=model_name,
            response_text=response_text,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cached_input_tokens=0,
            cached_output_tokens=0,
            latency_ms=latency_ms,
            actual_cost=compute_token_cost(
                model=model_name,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
            ),
        )
