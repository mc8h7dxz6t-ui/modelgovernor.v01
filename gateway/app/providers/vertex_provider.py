"""Google Vertex AI provider router."""
from __future__ import annotations

import time
import uuid

from fastapi import HTTPException

from ..config import Settings
from ..pricing import compute_token_cost
from .base import ProviderDispatchResult


class VertexProvider:
    def dispatch(
        self,
        *,
        settings: Settings,
        model: str,
        prompt: str | None,
        messages: list[dict[str, str]] | None,
    ) -> ProviderDispatchResult:
        if not settings.vertex_project_id:
            raise HTTPException(status_code=503, detail="VERTEX_PROJECT_ID is not configured")

        import vertexai
        from vertexai.generative_models import GenerativeModel

        model_name = model.split("/")[-1]
        vertexai.init(project=settings.vertex_project_id, location=settings.vertex_location)
        content = prompt or (messages[-1]["content"] if messages else "")
        started = time.monotonic()
        generative_model = GenerativeModel(model_name)
        response = generative_model.generate_content(content)
        latency_ms = int((time.monotonic() - started) * 1000)
        usage = getattr(response, "usage_metadata", None)
        input_tokens = int(getattr(usage, "prompt_token_count", 0) or 0)
        output_tokens = int(getattr(usage, "candidates_token_count", 0) or 0)
        if input_tokens == 0:
            input_tokens = max(len(content) // 4, 1)
        if output_tokens == 0:
            output_tokens = max(len(str(response.text or "")) // 4, 1)
        return ProviderDispatchResult(
            provider_request_id=f"vertex-{uuid.uuid4().hex[:16]}",
            provider_name="vertex",
            model=model_name,
            response_text=str(response.text or ""),
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
