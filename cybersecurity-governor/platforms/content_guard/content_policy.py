"""Content classification — PII/secret patterns before publish."""
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class ContentPattern:
    name: str
    pattern: re.Pattern[str]
    block_on_restricted: bool = True
    redact_on_internal: bool = True


@dataclass(frozen=True)
class ContentEvaluation:
    approved: bool
    decision: str
    risk_score: float
    matched_patterns: tuple[str, ...]
    redacted_body: str | None
    reason: str | None


_DEFAULT_PATTERNS = (
    ContentPattern("pii_ssn", re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
    ContentPattern("secret_api_key", re.compile(r"\bsk-[a-zA-Z0-9]{20,}\b")),
    ContentPattern(
        "pii_pan",
        re.compile(r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b"),
        block_on_restricted=False,
        redact_on_internal=True,
    ),
)


def _redact_matches(text: str, patterns: tuple[ContentPattern, ...]) -> str:
    redacted = text
    for pat in patterns:
        redacted = pat.pattern.sub(f"[REDACTED:{pat.name}]", redacted)
    return redacted


def evaluate_content(
    *,
    text_body: str,
    channel: str,
    classification_hint: str,
    principal_id: str,
    patterns: tuple[ContentPattern, ...] = _DEFAULT_PATTERNS,
) -> ContentEvaluation:
    if not principal_id or principal_id == "unknown":
        return ContentEvaluation(False, "BLOCKED", 1.0, (), None, "unknown principal")

    matched: list[str] = []
    for pat in patterns:
        if pat.pattern.search(text_body):
            matched.append(pat.name)

    if not matched:
        return ContentEvaluation(True, "ALLOWED", 0.05, (), None, None)

    classification = classification_hint.lower()
    channel_l = channel.lower()

    if "secret_api_key" in matched or "pii_ssn" in matched:
        return ContentEvaluation(
            False,
            "BLOCKED",
            0.95,
            tuple(matched),
            None,
            f"sensitive pattern blocked: {', '.join(matched)}",
        )

    if "pii_pan" in matched and classification in {"restricted", "confidential"}:
        return ContentEvaluation(
            False,
            "BLOCKED",
            0.9,
            tuple(matched),
            None,
            "payment card data blocked on restricted classification",
        )

    if "pii_pan" in matched and channel_l in {"publish", "email", "api"}:
        return ContentEvaluation(
            True,
            "REDACTED",
            0.6,
            tuple(matched),
            _redact_matches(text_body, patterns),
            "payment card data redacted",
        )

    return ContentEvaluation(
        False,
        "BLOCKED",
        0.85,
        tuple(matched),
        None,
        f"content blocked: {', '.join(matched)}",
    )
