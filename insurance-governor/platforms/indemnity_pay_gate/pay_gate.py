"""Indemnity payment gate — semantic beneficiary verification (Crime / FI bond loss control)."""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class PayeeGoldenRecord:
    payee_name: str
    payee_account: str
    expected_amount: Decimal
    max_amount_ratio: Decimal = Decimal("1.25")
    jurisdiction: str = "US"


@dataclass(frozen=True)
class IndemnityEvaluation:
    approved: bool
    decision: str
    score: float
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


def evaluate_indemnity_payment(
    *,
    payment_id: str,
    payee_name: str,
    payee_account: str,
    amount: Decimal,
    golden: PayeeGoldenRecord,
    min_semantic_score: float = 0.65,
    social_engineering_flag: bool = False,
) -> IndemnityEvaluation:
    if social_engineering_flag:
        return IndemnityEvaluation(False, "BLOCKED", 0.0, "social_engineering_alert")

    name_score = _token_overlap(payee_name, golden.payee_name)
    acct_match = payee_account.strip().upper() == golden.payee_account.strip().upper()
    acct_score = 1.0 if acct_match else 0.0
    score = 0.75 * name_score + 0.25 * acct_score

    if amount > golden.expected_amount * golden.max_amount_ratio:
        return IndemnityEvaluation(False, "HELD", score, "amount_anomaly_fat_finger")

    if score < min_semantic_score:
        return IndemnityEvaluation(False, "HELD", score, "payee_mismatch_crime_risk")

    return IndemnityEvaluation(True, "APPROVED", score)


DEFAULT_GOLDEN_US = PayeeGoldenRecord(
    payee_name="Acme Indemnity Trust",
    payee_account="US44ACME001",
    expected_amount=Decimal("2500000.00"),
    jurisdiction="US",
)

DEFAULT_GOLDEN_UK = PayeeGoldenRecord(
    payee_name="Lloyd's Syndicate 1234 Claims",
    payee_account="GB29LOYD1234",
    expected_amount=Decimal("1500000.00"),
    jurisdiction="UK",
)

GOLDEN_BY_JURISDICTION = {
    "US": DEFAULT_GOLDEN_US,
    "UK": DEFAULT_GOLDEN_UK,
    "GB": DEFAULT_GOLDEN_UK,
}
