"""FX rate snapshot with tamper-evident hash."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal


@dataclass(frozen=True)
class FxSnapshot:
    base: str
    quote: str
    rate: Decimal
    source: str
    captured_at: datetime
    fx_hash: str


def capture_fx_rate(
    *,
    base: str,
    quote: str,
    rate: Decimal,
    source: str = "ecb-mock",
) -> FxSnapshot:
    captured_at = datetime.now(timezone.utc)
    body = json.dumps(
        {
            "base": base,
            "quote": quote,
            "rate": str(rate),
            "source": source,
            "captured_at": captured_at.isoformat(),
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    fx_hash = hashlib.sha256(body.encode()).hexdigest()
    return FxSnapshot(
        base=base,
        quote=quote,
        rate=rate,
        source=source,
        captured_at=captured_at,
        fx_hash=fx_hash,
    )


def within_tolerance(
    amount_a: Decimal,
    amount_b: Decimal,
    fx_rate: Decimal,
    tolerance_pct: Decimal = Decimal("0.01"),
) -> bool:
    converted = amount_a * fx_rate
    if converted == 0:
        return amount_b == 0
    diff = abs(converted - amount_b) / abs(converted)
    return diff <= tolerance_pct
