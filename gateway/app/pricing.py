"""Token pricing for provider cost settlement."""
from __future__ import annotations

from decimal import Decimal

from .money import quantize_money

# Per-token input/output USD rates aligned with model_policy_registry seeds.
MODEL_TOKEN_PRICING: dict[str, tuple[Decimal, Decimal]] = {
    "gpt-4o-mini": (Decimal("0.00000015"), Decimal("0.00000060")),
    "gpt-4.1-mini": (Decimal("0.00000025"), Decimal("0.00000100")),
    "claude-3-5-haiku-latest": (Decimal("0.00000025"), Decimal("0.00000125")),
    "claude-3-haiku-20240307": (Decimal("0.00000025"), Decimal("0.00000125")),
    "gemini-1.5-flash": (Decimal("0.000000075"), Decimal("0.00000030")),
    "gemini-1.5-pro": (Decimal("0.00000125"), Decimal("0.00000500")),
}

DEFAULT_TOKEN_PRICING = (Decimal("0.00000050"), Decimal("0.00000150"))


def compute_token_cost(
    *,
    model: str,
    input_tokens: int,
    output_tokens: int,
    cached_input_tokens: int = 0,
) -> Decimal:
    model_key = model.split("/")[-1]
    input_rate, output_rate = MODEL_TOKEN_PRICING.get(model_key, DEFAULT_TOKEN_PRICING)
    billable_input = max(input_tokens - cached_input_tokens, 0)
    total = (Decimal(billable_input) * input_rate) + (Decimal(output_tokens) * output_rate)
    return quantize_money(total)
