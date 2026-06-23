"""Mock provider for development and CI."""
from __future__ import annotations

import time
import uuid
from decimal import Decimal

from ..config import Settings
from ..pricing import compute_token_cost
from .base import ProviderDispatchResult


class MockProvider:
    def dispatch(
        self,
        *,
        settings: Settings,
        model: str,
        prompt: str | None,
        messages: list[dict[str, str]] | None,
    ) -> ProviderDispatchResult:
        started = time.monotonic()
        content = prompt or (messages[-1]["content"] if messages else "mock-response")
        input_tokens = max(len(content) // 4, 1)
        output_tokens = max(int(settings.mock_output_tokens), 1)
        actual_cost = min(
            compute_token_cost(model=model, input_tokens=input_tokens, output_tokens=output_tokens),
            settings.mock_dispatch_cost,
        )
        latency_ms = int((time.monotonic() - started) * 1000)
        return ProviderDispatchResult(
            provider_request_id=f"mock-{uuid.uuid4().hex[:16]}",
            provider_name="mock",
            model=model,
            response_text=f"mock:{content[:120]}",
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cached_input_tokens=0,
            cached_output_tokens=0,
            latency_ms=latency_ms,
            actual_cost=actual_cost,
        )
