"""Underwriting governance — fair lending / bias gate (D&O / regulatory liability loss control)."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


# UK: FCA Consumer Duty / Equality Act protected characteristics (subset)
# US: FCRA / ECOA adverse action triggers (subset)
PROTECTED_ATTRIBUTES = frozenset(
    {"age_band", "gender", "ethnicity", "postcode_sector", "zip_code", "marital_status"}
)


@dataclass(frozen=True)
class UnderwritingEvaluation:
    compliant: bool
    decision: str
    bias_score: float
    reason: str | None
    adverse_action_required: bool = False


def evaluate_underwriting_fairness(
    *,
    application_id: str,
    score: float,
    protected_attribute_deltas: dict[str, float],
    jurisdiction: str = "US",
    max_disparate_impact: float = 0.15,
    auto_approve_limit: Decimal = Decimal("500000"),
    requested_limit: Decimal = Decimal("0"),
) -> UnderwritingEvaluation:
    if not protected_attribute_deltas:
        if requested_limit > auto_approve_limit:
            return UnderwritingEvaluation(True, "COMPLIANT", 0.0, "manual_review_escalation", False)
        return UnderwritingEvaluation(True, "COMPLIANT", 0.0, None)

    max_delta = max(abs(v) for v in protected_attribute_deltas.values())
    flagged = [k for k in protected_attribute_deltas if k in PROTECTED_ATTRIBUTES and abs(protected_attribute_deltas[k]) > max_disparate_impact]

    if flagged:
        return UnderwritingEvaluation(
            False,
            "VIOLATION",
            max_delta,
            f"disparate_impact:{','.join(flagged)}",
            adverse_action_required=jurisdiction.upper() in ("US", "UK", "GB"),
        )

    if max_delta > max_disparate_impact * 0.8:
        return UnderwritingEvaluation(True, "REFERRED", max_delta, "elevated_bias_score", False)

    return UnderwritingEvaluation(True, "COMPLIANT", max_delta, None)
