"""Canonical transaction hash for intercompany pairing."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class TxnRecord:
    entity_id: str
    counterparty_id: str
    amount: Decimal
    currency: str
    value_date: str
    reference: str


def txn_hash(txn: TxnRecord) -> str:
    body = json.dumps(
        {
            "entity_id": txn.entity_id,
            "counterparty_id": txn.counterparty_id,
            "amount": str(txn.amount),
            "currency": txn.currency,
            "value_date": txn.value_date,
            "reference": txn.reference.strip().lower(),
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(body.encode()).hexdigest()
