"""Shared governor spine configuration — authoritative ports and ledger table names."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import FrozenSet


class GovernorDomain(Enum):
    MODEL = "MODEL_GOVERNOR"
    FINANCE = "FINANCE_GOVERNOR"
    INSURANCE = "INSURANCE_GOVERNOR"
    CYBER = "CYBER_GOVERNOR"


@dataclass(frozen=True)
class SpinePortMap:
    gateway: int
    sidecar: int
    reconciler: int
    postgres_host: int
    redis_host: int


@dataclass(frozen=True)
class TableSchemaConfig:
    """Maps a governor to its primary hash-chained ledger table (public schema today)."""

    ledger_table: str
    anchor_table: str
    verify_path: str
    required_facets: FrozenSet[str] = field(default_factory=frozenset)


DOMAIN_PORTS: dict[GovernorDomain, SpinePortMap] = {
    GovernorDomain.MODEL: SpinePortMap(8080, 8081, 8082, 5432, 6379),
    GovernorDomain.FINANCE: SpinePortMap(8090, 8091, 8092, 5433, 6380),
    GovernorDomain.INSURANCE: SpinePortMap(8100, 8101, 8102, 5434, 6381),
    GovernorDomain.CYBER: SpinePortMap(8120, 8121, 8122, 5434, 6381),
}

DOMAIN_REGISTRY: dict[GovernorDomain, TableSchemaConfig] = {
    GovernorDomain.MODEL: TableSchemaConfig(
        ledger_table="ledger_events",
        anchor_table="ledger_chain_anchors",
        verify_path="/internal/ledger/verify-chain",
        required_facets=frozenset({"user_id", "provider", "model"}),
    ),
    GovernorDomain.FINANCE: TableSchemaConfig(
        ledger_table="decision_events",
        anchor_table="decision_chain_anchors",
        verify_path="/internal/decisions/verify-chain",
        required_facets=frozenset({"account_id", "operation_id", "policy_id"}),
    ),
    GovernorDomain.INSURANCE: TableSchemaConfig(
        ledger_table="claim_events",
        anchor_table="claim_chain_anchors",
        verify_path="/internal/claims/verify-chain",
        required_facets=frozenset({"account_id", "operation_id", "policy_id"}),
    ),
    GovernorDomain.CYBER: TableSchemaConfig(
        ledger_table="security_events",
        anchor_table="security_chain_anchors",
        verify_path="/internal/security/verify-chain",
        required_facets=frozenset({"operation_id", "platform", "policy_id"}),
    ),
}

MATURITY_LABEL = "L5 Institutional Self-Check Certified"
