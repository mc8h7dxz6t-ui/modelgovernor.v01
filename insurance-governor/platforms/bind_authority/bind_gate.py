"""BindAuthority — governed policy bind gate."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from platforms.common.crystal import canonical_fingerprint


@dataclass(frozen=True)
class BindEvaluation:
    approved: bool
    decision: str
    reason: str | None
    score: float


def evaluate_bind(
    *,
    application_id: str,
    premium: Decimal,
    limit: Decimal,
    auto_bind_premium: Decimal,
    sanctions_flag: bool = False,
    manual_review_flag: bool = False,
) -> BindEvaluation:
    if sanctions_flag:
        return BindEvaluation(approved=False, decision="DECLINED", reason="sanctions_hit", score=0.0)
    if manual_review_flag:
        return BindEvaluation(approved=False, decision="REFERRED", reason="underwriting_review", score=0.3)
    if limit <= 0:
        return BindEvaluation(approved=False, decision="DECLINED", reason="invalid_limit", score=0.0)
    if premium > auto_bind_premium:
        return BindEvaluation(approved=False, decision="HELD", reason="above_auto_bind_premium", score=0.5)
    return BindEvaluation(approved=True, decision="BOUND", reason=None, score=1.0)


def bind_facets(
    *,
    application_id: str,
    premium: Decimal,
    limit: Decimal,
    currency: str,
    decision: str,
    score: float,
) -> dict:
    prem = str(premium)
    lim = str(limit)
    return {
        "application_id": application_id,
        "premium": prem,
        "limit": lim,
        "currency": currency,
        "bind_decision": decision,
        "bind_score": score,
        "bind_fingerprint": canonical_fingerprint(
            "bind_authority",
            application_id,
            {"premium": prem, "limit": lim, "currency": currency},
        ),
    }
