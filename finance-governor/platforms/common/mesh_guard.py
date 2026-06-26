"""Crystal mesh — cross-platform guards (e.g. no wire while desk FROZEN)."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .platform_metrics import get_platform_metrics


class DeskState(str, Enum):
    ACTIVE = "ACTIVE"
    DEGRADED = "DEGRADED"
    FROZEN = "FROZEN"


@dataclass
class MeshGuard:
    """Shared desk state across AlgoFreeze, WireMatch, CreditGovern."""

    desk_id: str = "desk-default"
    algo_state: DeskState = DeskState.ACTIVE
    freeze_reason: str | None = None

    def set_algo_frozen(self, reason: str) -> None:
        self.algo_state = DeskState.FROZEN
        self.freeze_reason = reason

    def set_algo_active(self) -> None:
        self.algo_state = DeskState.ACTIVE
        self.freeze_reason = None

    def allows_wire_send(self) -> tuple[bool, str | None]:
        if self.algo_state == DeskState.FROZEN:
            get_platform_metrics().increment("crystal_mesh_block_total")
            return False, f"MESH_BLOCK: algo desk {self.desk_id} FROZEN ({self.freeze_reason})"
        return True, None

    def allows_credit_score(self) -> tuple[bool, str | None]:
        if self.algo_state == DeskState.FROZEN:
            get_platform_metrics().increment("crystal_mesh_block_total")
            return False, f"MESH_BLOCK: desk {self.desk_id} FROZEN"
        return True, None


# Process-local singleton for standalone demos; spine mode uses sidecar state.
_mesh = MeshGuard()


def get_mesh_guard() -> MeshGuard:
    return _mesh
