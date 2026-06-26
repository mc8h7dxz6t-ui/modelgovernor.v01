"""IC match engine — FX-hash at clear, not month-end Duco-style batch."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from platforms.common.platform_metrics import get_platform_metrics

from .fx_snapshot import FxSnapshot


@dataclass(frozen=True)
class IcTransaction:
    txn_hash: str
    entity_id: str
    counterparty_id: str
    amount: Decimal
    currency: str


@dataclass(frozen=True)
class MatchResult:
    matched: bool
    pair_id: str | None = None
    fx_snapshot_hash: str | None = None
    reason: str | None = None
    converted_delta: Decimal | None = None


class MatchEngine:
    def __init__(self, *, tolerance_bps: int = 5) -> None:
        self._tolerance_bps = tolerance_bps
        self._matched_hashes: set[str] = set()
        self._pending: dict[str, IcTransaction] = {}

    def ingest(self, txn: IcTransaction) -> MatchResult | None:
        metrics = get_platform_metrics()
        if txn.txn_hash in self._matched_hashes:
            metrics.increment("match_tolerance_breach_total")
            return MatchResult(matched=False, reason="DUPLICATE_TXN_HASH")

        mirror_key = self._mirror_key(txn)
        pending = self._pending.get(mirror_key)
        if pending is None:
            self._pending[self._own_key(txn)] = txn
            return None

        return self._attempt_match(pending, txn)

    @staticmethod
    def _own_key(txn: IcTransaction) -> str:
        return f"{txn.entity_id}:{txn.counterparty_id}:{txn.currency}"

    @staticmethod
    def _mirror_key(txn: IcTransaction) -> str:
        return f"{txn.counterparty_id}:{txn.entity_id}:{txn.currency}"

    def _attempt_match(self, a: IcTransaction, b: IcTransaction, fx: FxSnapshot | None = None) -> MatchResult:
        metrics = get_platform_metrics()
        pair_id = f"{a.txn_hash[:8]}-{b.txn_hash[:8]}"

        if a.amount.copy_abs() != b.amount.copy_abs():
            tolerance = a.amount.copy_abs() * Decimal(self._tolerance_bps) / Decimal(10000)
            delta = (a.amount.copy_abs() - b.amount.copy_abs()).copy_abs()
            if delta > tolerance:
                metrics.increment("match_tolerance_breach_total")
                return MatchResult(matched=False, pair_id=pair_id, reason="AMOUNT_TOLERANCE_BREACH", converted_delta=delta)

        fx_hash = fx.snapshot_hash if fx else "no-fx"
        self._matched_hashes.add(a.txn_hash)
        self._matched_hashes.add(b.txn_hash)
        self._pending.pop(self._own_key(a), None)
        self._pending.pop(self._own_key(b), None)
        metrics.increment("ic_match_success_total")
        return MatchResult(matched=True, pair_id=pair_id, fx_snapshot_hash=fx_hash)

    def match_with_fx(self, a: IcTransaction, b: IcTransaction, fx: FxSnapshot) -> MatchResult:
        return self._attempt_match(a, b, fx)

    def orphan_count(self) -> int:
        return len(self._pending)

    def sweep_orphans(self) -> int:
        metrics = get_platform_metrics()
        count = len(self._pending)
        if count:
            metrics.increment("ic_orphan_detected_total", count)
        self._pending.clear()
        return count
