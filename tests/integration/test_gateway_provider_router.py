"""Gateway provider router and pricing tests."""
from __future__ import annotations

from decimal import Decimal
from pathlib import Path
import sys
from unittest.mock import MagicMock, patch

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from gateway.app.config import Settings
from gateway.app.pricing import compute_token_cost, estimate_chat_reserve_cost
from gateway.app.providers.router import ProviderRouter, _resolve_provider_name


def test_estimate_chat_reserve_cost() -> None:
    from gateway.app.config import Settings

    settings = Settings(provider_max_output_tokens=512)
    cost = estimate_chat_reserve_cost(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "hello"}],
        max_tokens=100,
        settings=settings,
    )
    assert cost >= Decimal("0.010000")


def test_compute_token_cost_micro_precision() -> None:
    cost = compute_token_cost(model="gpt-4o-mini", input_tokens=1000, output_tokens=500)
    assert cost > Decimal("0")
    assert cost == Decimal("0.000450000000")


def test_resolve_provider_name() -> None:
    assert _resolve_provider_name("gpt-4o-mini") == "openai"
    assert _resolve_provider_name("anthropic/claude-3-5-haiku-latest") == "anthropic"
    assert _resolve_provider_name("vertex/gemini-1.5-flash") == "vertex"


def test_mock_provider_dispatch() -> None:
    settings = Settings(
        sidecar_internal_token="token",
        provider_mode="mock",
        mock_dispatch_cost=Decimal("2.000000"),
    )
    router = ProviderRouter()
    result = router.dispatch(
        settings=settings,
        model="gpt-4o-mini",
        prompt="hello world",
        messages=None,
    )
    assert result.provider_name == "mock"
    assert result.actual_cost <= Decimal("2.000000")
    assert result.input_tokens > 0
    assert result.output_tokens > 0


def test_openai_provider_dispatch_with_mocked_sdk() -> None:
    pytest.importorskip("openai")
    settings = Settings(
        sidecar_internal_token="token",
        provider_mode="live",
        openai_api_key="test-key",
    )
    usage = MagicMock(prompt_tokens=100, completion_tokens=50)
    message = MagicMock(content="provider response")
    choice = MagicMock(message=message)
    response = MagicMock(id="req-123", usage=usage, choices=[choice])
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = response

    with patch("openai.OpenAI", return_value=mock_client):
        router = ProviderRouter()
        result = router.dispatch(
            settings=settings,
            model="gpt-4o-mini",
            prompt="hello",
            messages=None,
        )
    assert result.provider_name == "openai"
    assert result.provider_request_id == "req-123"
    assert result.response_text == "provider response"
    assert result.actual_cost > Decimal("0")
