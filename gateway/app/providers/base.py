"""Provider dispatch result mapped to sidecar settle semantics."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class ProviderDispatchResult:
    provider_request_id: str
    provider_name: str
    model: str
    response_text: str
    input_tokens: int
    output_tokens: int
    cached_input_tokens: int
    cached_output_tokens: int
    latency_ms: int
    actual_cost: Decimal
