"""Intercompany match engine."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from .fx_snapshot import FxSnapshot, within_tolerance
from .txn_hasher import TxnRecord, txn_hash


@dataclass(frozen=True)
class MatchResult:
    matched: bool
    txn_hash: str
    mirror_hash: str | None
    reason: str | None = None
    fx_hash: str | None = None


def find_mirror(
    txn: TxnRecord,
    pending: list[TxnRecord],
    fx: FxSnapshot,
) -> MatchResult:
    th = txn_hash(txn)
    for candidate in pending:
        if candidate.entity_id != txn.counterparty_id or candidate.counterparty_id != txn.entity_id:
            continue
        if candidate.currency != txn.currency and fx.base != txn.currency:
            continue
        if not within_tolerance(txn.amount, candidate.amount, fx.rate):
            continue
        return MatchResult(
            matched=True,
            txn_hash=th,
            mirror_hash=txn_hash(candidate),
            fx_hash=fx.fx_hash,
        )
    return MatchResult(matched=False, txn_hash=th, mirror_hash=None, reason="NO_MIRROR_OR_FX_DRIFT")
