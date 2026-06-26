"""SubledgerSync — FX snapshot at match time (vs BlackLine month-end batch)."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal


@dataclass(frozen=True)
class FxSnapshot:
    base_currency: str
    quote_currency: str
    rate: Decimal
    source: str
    fetched_at: str
    snapshot_hash: str


def capture_fx_snapshot(
    *,
    base_currency: str,
    quote_currency: str,
    rate: Decimal,
    source: str = "ECB",
) -> FxSnapshot:
    fetched_at = datetime.now(timezone.utc).isoformat()
    body = {
        "base": base_currency,
        "quote": quote_currency,
        "rate": str(rate),
        "source": source,
        "fetched_at": fetched_at,
    }
    snapshot_hash = hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()
    return FxSnapshot(
        base_currency=base_currency,
        quote_currency=quote_currency,
        rate=rate,
        source=source,
        fetched_at=fetched_at,
        snapshot_hash=snapshot_hash,
    )
