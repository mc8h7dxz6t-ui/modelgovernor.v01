"""OpenAI-compatible HTTP API (/v1/chat/completions, /v1/models)."""
from __future__ import annotations

import time
import uuid
from decimal import Decimal
from typing import Any, Literal

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field

from .config import Settings, get_settings
from .governance import execute_governed_dispatch
from .openai_auth import OpenAICompatAuth, require_openai_compat_auth
from .pricing import estimate_chat_reserve_cost

router = APIRouter(prefix="/v1", tags=["openai-compat"])

OPENAI_MODEL_CATALOG: list[dict[str, Any]] = [
    {"id": "gpt-4o-mini", "object": "model", "created": 1686935002, "owned_by": "openai"},
    {"id": "gpt-4.1-mini", "object": "model", "created": 1715443200, "owned_by": "openai"},
    {"id": "anthropic/claude-3-5-haiku-latest", "object": "model", "created": 1715443200, "owned_by": "anthropic"},
    {"id": "vertex/gemini-1.5-flash", "object": "model", "created": 1715443200, "owned_by": "google"},
]


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant", "tool", "developer"]
    content: str | list[Any] | None = None


class ChatCompletionRequest(BaseModel):
    model: str = Field(..., min_length=1, max_length=255)
    messages: list[ChatMessage] = Field(..., min_length=1)
    max_tokens: int | None = Field(default=None, ge=1)
    temperature: float | None = None
    user: str | None = Field(default=None, max_length=255)
    stream: bool | None = False


def _message_content_to_str(content: str | list[Any] | None) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    parts: list[str] = []
    for item in content:
        if isinstance(item, dict):
            text = item.get("text")
            if text:
                parts.append(str(text))
        else:
            parts.append(str(item))
    return " ".join(parts)


def _messages_to_provider(messages: list[ChatMessage]) -> list[dict[str, str]]:
    return [
        {"role": message.role, "content": _message_content_to_str(message.content)}
        for message in messages
    ]


def _resolve_user_id(
    request: ChatCompletionRequest,
    x_mg_user_id: str | None,
    settings: Settings,
) -> str:
    if x_mg_user_id and x_mg_user_id.strip():
        return x_mg_user_id.strip()
    if request.user and request.user.strip():
        return request.user.strip()
    return settings.openai_compat_default_user_id


def _resolve_trace_id(x_mg_trace_id: str | None, user_id: str) -> str:
    if x_mg_trace_id and x_mg_trace_id.strip():
        return x_mg_trace_id.strip()
    return f"openai-{user_id}"


def _chat_completion_response(
    *,
    model: str,
    content: str,
    input_tokens: int,
    output_tokens: int,
    provider_request_id: str,
) -> dict[str, Any]:
    created = int(time.time())
    completion_id = provider_request_id if provider_request_id.startswith("chatcmpl-") else f"chatcmpl-{uuid.uuid4().hex[:24]}"
    return {
        "id": completion_id,
        "object": "chat.completion",
        "created": created,
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": input_tokens,
            "completion_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
        },
    }


@router.get("/models")
def list_models(
    _auth: OpenAICompatAuth = Depends(require_openai_compat_auth),
) -> dict[str, Any]:
    return {"object": "list", "data": OPENAI_MODEL_CATALOG}


@router.get("/models/{model_id}")
def retrieve_model(
    model_id: str,
    _auth: OpenAICompatAuth = Depends(require_openai_compat_auth),
) -> dict[str, Any]:
    for entry in OPENAI_MODEL_CATALOG:
        if entry["id"] == model_id:
            return entry
    raise HTTPException(
        status_code=404,
        detail={
            "error": {
                "message": f"The model '{model_id}' does not exist.",
                "type": "invalid_request_error",
                "code": "model_not_found",
            }
        },
    )


@router.post("/chat/completions")
def chat_completions(
    request: ChatCompletionRequest,
    auth: OpenAICompatAuth = Depends(require_openai_compat_auth),
    x_mg_user_id: str | None = Header(default=None),
    x_mg_trace_id: str | None = Header(default=None),
    x_mg_idempotency_key: str | None = Header(default=None),
) -> dict[str, Any]:
    if request.stream:
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "message": "Streaming is not supported yet. Set stream=false.",
                    "type": "invalid_request_error",
                    "code": "unsupported_stream",
                }
            },
        )

    settings = get_settings()
    if not settings.openai_compat_enabled:
        raise HTTPException(status_code=404, detail="OpenAI-compatible API is disabled")

    provider_messages = _messages_to_provider(request.messages)
    user_id = _resolve_user_id(request, x_mg_user_id, settings)
    trace_id = _resolve_trace_id(x_mg_trace_id, user_id)
    estimated_cost = estimate_chat_reserve_cost(
        model=request.model,
        messages=provider_messages,
        max_tokens=request.max_tokens,
        settings=settings,
    )

    outcome = execute_governed_dispatch(
        settings=settings,
        user_id=user_id,
        trace_id=trace_id,
        model=request.model,
        estimated_cost=estimated_cost,
        idempotency_key=x_mg_idempotency_key,
        prompt=None,
        messages=provider_messages,
        auth_subject=auth.subject,
    )
    return _chat_completion_response(
        model=outcome.model,
        content=outcome.response_text,
        input_tokens=outcome.input_tokens,
        output_tokens=outcome.output_tokens,
        provider_request_id=outcome.provider_request_id,
    )
