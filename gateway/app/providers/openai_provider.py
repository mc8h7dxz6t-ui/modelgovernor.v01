"""OpenAI provider router."""
from __future__ import annotations

import time
import uuid

from fastapi import HTTPException

from ..config import Settings
from ..pricing import compute_token_cost
from .base import ProviderDispatchResult


class OpenAIProvider:
    def dispatch(
        self,
        *,
        settings: Settings,
        model: str,
        prompt: str | None,
        messages: list[dict[str, str]] | None,
    ) -> ProviderDispatchResult:
        if not settings.openai_api_key:
            raise HTTPException(status_code=503, detail="OPENAI_API_KEY is not configured")

        from openai import OpenAI

        model_name = model.split("/")[-1]
        chat_messages = messages or [{"role": "user", "content": prompt or ""}]
        started = time.monotonic()
        client = OpenAI(api_key=settings.openai_api_key, timeout=settings.provider_timeout_seconds)
        response = client.chat.completions.create(model=model_name, messages=chat_messages)
        latency_ms = int((time.monotonic() - started) * 1000)
        usage = response.usage
        input_tokens = int(usage.prompt_tokens if usage else 0)
        output_tokens = int(usage.completion_tokens if usage else 0)
        request_id = response.id or f"openai-{uuid.uuid4().hex[:16]}"
        response_text = response.choices[0].message.content or ""
        return ProviderDispatchResult(
            provider_request_id=request_id,
            provider_name="openai",
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
