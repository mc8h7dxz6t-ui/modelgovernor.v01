"""CreditGovern exposure ledger — reserve-before-score vs ValidMind docs-only MRM."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass
class DeskExposure:
    desk_id: str
    cap_amount: Decimal
    reserved_total: Decimal = Decimal("0")
    locked: bool = False


class ExposureLedger:
    def __init__(self) -> None:
        self._desks: dict[str, DeskExposure] = {}

    def ensure_desk(self, desk_id: str, cap_amount: Decimal) -> DeskExposure:
        if desk_id not in self._desks:
            self._desks[desk_id] = DeskExposure(desk_id=desk_id, cap_amount=cap_amount)
        return self._desks[desk_id]

    def reserve(self, desk_id: str, amount: Decimal) -> tuple[bool, str | None]:
        desk = self._desks.get(desk_id)
        if desk is None:
            return False, "UNKNOWN_DESK"
        if desk.locked:
            return False, "DESK_LOCKED"
        if desk.reserved_total + amount > desk.cap_amount:
            return False, "INSUFFICIENT_EXPOSURE"
        if desk.reserved_total + amount < 0:
            return False, "NEGATIVE_BALANCE"
        desk.reserved_total += amount
        return True, None

    def settle(self, desk_id: str, reserved_amount: Decimal, actual_amount: Decimal) -> None:
        desk = self._desks[desk_id]
        desk.reserved_total -= reserved_amount
        desk.reserved_total += actual_amount

    def refund_reserve(self, desk_id: str, amount: Decimal) -> None:
        desk = self._desks[desk_id]
        desk.reserved_total -= amount

    def snapshot(self, desk_id: str) -> dict:
        desk = self._desks[desk_id]
        return {
            "desk_id": desk.desk_id,
            "cap_amount": str(desk.cap_amount),
            "reserved_total": str(desk.reserved_total),
            "locked": desk.locked,
        }
