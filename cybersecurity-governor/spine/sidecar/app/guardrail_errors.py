"""Shared guardrail denial exceptions."""


class GuardrailError(Exception):
    pass


class RateLimitExceeded(GuardrailError):
    pass


class TraceDepthExceeded(GuardrailError):
    pass


class InflightLimitExceeded(GuardrailError):
    pass
