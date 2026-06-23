"""Route governed dispatch to OpenAI, Anthropic, Vertex, or mock providers."""
from __future__ import annotations

from fastapi import HTTPException

from ..config import Settings
from .anthropic_provider import AnthropicProvider
from .base import ProviderDispatchResult
from .mock_provider import MockProvider
from .openai_provider import OpenAIProvider
from .vertex_provider import VertexProvider


def _resolve_provider_name(model: str) -> str:
    normalized = model.strip().lower()
    if normalized.startswith("openai/"):
        return "openai"
    if normalized.startswith("anthropic/"):
        return "anthropic"
    if normalized.startswith("vertex/") or normalized.startswith("google/"):
        return "vertex"
    if normalized.startswith("claude"):
        return "anthropic"
    if normalized.startswith("gemini"):
        return "vertex"
    if normalized.startswith("gpt"):
        return "openai"
    raise HTTPException(status_code=400, detail=f"unsupported provider model: {model}")


class ProviderRouter:
    def __init__(self) -> None:
        self._openai = OpenAIProvider()
        self._anthropic = AnthropicProvider()
        self._vertex = VertexProvider()
        self._mock = MockProvider()

    def dispatch(
        self,
        *,
        settings: Settings,
        model: str,
        prompt: str | None,
        messages: list[dict[str, str]] | None,
    ) -> ProviderDispatchResult:
        if settings.provider_mode == "mock":
            return self._mock.dispatch(
                settings=settings,
                model=model,
                prompt=prompt,
                messages=messages,
            )

        if not prompt and not messages:
            raise HTTPException(
                status_code=400,
                detail="prompt or messages required for live provider dispatch",
            )

        provider_name = _resolve_provider_name(model)
        if provider_name == "openai":
            return self._openai.dispatch(
                settings=settings,
                model=model,
                prompt=prompt,
                messages=messages,
            )
        if provider_name == "anthropic":
            return self._anthropic.dispatch(
                settings=settings,
                model=model,
                prompt=prompt,
                messages=messages,
            )
        return self._vertex.dispatch(
            settings=settings,
            model=model,
            prompt=prompt,
            messages=messages,
        )


_router: ProviderRouter | None = None


def get_provider_router() -> ProviderRouter:
    global _router
    if _router is None:
        _router = ProviderRouter()
    return _router
