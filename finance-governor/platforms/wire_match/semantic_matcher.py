"""WireMatch — semantic beneficiary matching."""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class GoldenRecord:
    beneficiary_name: str
    beneficiary_account: str
    expected_amount: Decimal
    max_amount_ratio: Decimal = Decimal("1.5")


@dataclass(frozen=True)
class MatchResult:
    score: float
    approved: bool
    reason: str | None = None


def _normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def _token_overlap(a: str, b: str) -> float:
    ta, tb = set(_normalize(a).split()), set(_normalize(b).split())
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / max(len(ta), len(tb))


def evaluate_wire(
    *,
    beneficiary_name: str,
    beneficiary_account: str,
    amount: Decimal,
    golden: GoldenRecord,
    min_semantic_score: float = 0.6,
) -> MatchResult:
    name_score = _token_overlap(beneficiary_name, golden.beneficiary_name)
    acct_match = beneficiary_account.strip() == golden.beneficiary_account.strip()
    acct_score = 1.0 if acct_match else 0.0
    score = 0.7 * name_score + 0.3 * acct_score

    if amount > golden.expected_amount * golden.max_amount_ratio:
        return MatchResult(score=score, approved=False, reason="AMOUNT_ANOMALY")

    if score < min_semantic_score:
        return MatchResult(score=score, approved=False, reason="BENEFICIARY_MISMATCH")

    return MatchResult(score=score, approved=True)
