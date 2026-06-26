"""Canonical transaction hasher for cross-entity IC pairing."""
from __future__ import annotations

import hashlib
import json
from decimal import Decimal


def canonical_txn_hash(
    *,
    entity_id: str,
    counterparty_id: str,
    amount: Decimal,
    currency: str,
    reference: str,
    value_date: str,
) -> str:
    body = {
        "entity_id": entity_id,
        "counterparty_id": counterparty_id,
        "amount": str(amount),
        "currency": currency,
        "reference": reference.strip().upper(),
        "value_date": value_date,
    }
    return hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()
