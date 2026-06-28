"""Shared ledger seal contract — interface only (phase K1 extraction).

Governors implement sealing in their own ``*_seal.py`` modules. This contract documents
the required behaviors for Industry Leading 9/10 kernel parity without duplicating SQLAlchemy writers.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class ChainSealResult(Protocol):
    prev_hash: str
    row_hash: str


@runtime_checkable
class ChainVerifier(Protocol):
    def verify_chain(self, session: Any) -> dict[str, Any]:
        """Return {\"valid\": bool, ...} for HTTP verify-chain endpoints."""


@runtime_checkable
class LedgerSealer(Protocol):
    def seal_event(
        self,
        session: Any,
        *,
        event_id: int,
        prev_hash: str,
        payload: dict[str, Any],
    ) -> ChainSealResult:
        """Append prev_hash → row_hash for one ledger row."""


LEDGER_TABLE_BY_DOMAIN = {
    "MODEL_GOVERNOR": "ledger_events",
    "FINANCE_GOVERNOR": "decision_events",
    "INSURANCE_GOVERNOR": "claim_events",
    "CYBER_GOVERNOR": "security_events",
}
