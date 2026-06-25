"""AlgoFreeze — order egress gate."""
from __future__ import annotations

from .freeze_controller import FreezeController


class OrderGate:
    def __init__(self, controller: FreezeController) -> None:
        self._controller = controller
        self._blocked_attempts = 0

    @property
    def blocked_attempts(self) -> int:
        return self._blocked_attempts

    def allow_order(self) -> bool:
        if self._controller.allows_egress():
            return True
        self._blocked_attempts += 1
        return False
