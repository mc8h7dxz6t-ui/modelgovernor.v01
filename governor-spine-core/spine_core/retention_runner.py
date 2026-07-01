"""K4 — retention tier reporting and checkpoint-safe archival."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from spine_core.config import DOMAIN_REGISTRY, GovernorDomain


@dataclass(frozen=True)
class RetentionSpec:
    ledger_table: str
    policy_table: str
    checkpoint_table: str


RETENTION_REGISTRY: dict[GovernorDomain, RetentionSpec] = {
    GovernorDomain.MODEL: RetentionSpec(
        ledger_table="ledger_events",
        policy_table="ledger_events_retention_policy",
        checkpoint_table="ledger_chain_verify_checkpoints",
    ),
    GovernorDomain.FINANCE: RetentionSpec(
        ledger_table="decision_events",
        policy_table="decision_events_retention_policy",
        checkpoint_table="decision_chain_verify_checkpoints",
    ),
    GovernorDomain.INSURANCE: RetentionSpec(
        ledger_table="claim_events",
        policy_table="claim_events_retention_policy",
        checkpoint_table="claim_chain_verify_checkpoints",
    ),
    GovernorDomain.CYBER: RetentionSpec(
        ledger_table="security_events",
        policy_table="security_events_retention_policy",
        checkpoint_table="security_chain_verify_checkpoints",
    ),
}


@dataclass(frozen=True)
class RetentionPolicy:
    hot_days: int
    warm_days: int
    archive_enabled: bool


@dataclass
class RetentionReport:
    domain: GovernorDomain
    ledger_table: str
    total_events: int
    hot_count: int
    warm_count: int
    cold_count: int
    archived_count: int
    archive_skipped_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "domain": self.domain.value,
            "ledger_table": self.ledger_table,
            "total_events": self.total_events,
            "hot_count": self.hot_count,
            "warm_count": self.warm_count,
            "cold_count": self.cold_count,
            "archived_count": self.archived_count,
        }
        if self.archive_skipped_reason:
            payload["archive_skipped_reason"] = self.archive_skipped_reason
        return payload


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _table_exists(session: Session, table_name: str) -> bool:
    dialect = session.bind.dialect.name
    if dialect == "postgresql":
        row = session.execute(
            text(
                """
                SELECT 1
                FROM information_schema.tables
                WHERE table_schema = 'public' AND table_name = :table_name
                """
            ),
            {"table_name": table_name},
        ).first()
        return row is not None
    if dialect == "sqlite":
        row = session.execute(
            text("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = :table_name"),
            {"table_name": table_name},
        ).first()
        return row is not None
    return False


def load_retention_policy(session: Session, policy_table: str) -> RetentionPolicy:
    if not _table_exists(session, policy_table):
        return RetentionPolicy(hot_days=90, warm_days=365, archive_enabled=False)

    row = session.execute(
        text(
            f"""
            SELECT hot_days, warm_days, archive_enabled
            FROM {policy_table}
            WHERE policy_id = 'default'
            """
        )
    ).mappings().first()
    if not row:
        return RetentionPolicy(hot_days=90, warm_days=365, archive_enabled=False)
    return RetentionPolicy(
        hot_days=int(row["hot_days"]),
        warm_days=int(row["warm_days"]),
        archive_enabled=bool(row["archive_enabled"]),
    )


def _load_checkpoint_event_id(session: Session, checkpoint_table: str) -> int | None:
    if not _table_exists(session, checkpoint_table):
        return None
    row = session.execute(
        text(
            f"""
            SELECT last_verified_event_id
            FROM {checkpoint_table}
            WHERE singleton_key = 1
            """
        )
    ).first()
    return int(row[0]) if row else None


def _tier_counts(
    session: Session,
    *,
    ledger_table: str,
    hot_cutoff: datetime,
    warm_cutoff: datetime,
) -> tuple[int, int, int, int]:
    total = session.execute(text(f"SELECT COUNT(*) FROM {ledger_table}")).scalar_one()
    hot = session.execute(
        text(f"SELECT COUNT(*) FROM {ledger_table} WHERE recorded_at >= :hot_cutoff"),
        {"hot_cutoff": hot_cutoff},
    ).scalar_one()
    warm = session.execute(
        text(
            f"""
            SELECT COUNT(*) FROM {ledger_table}
            WHERE recorded_at < :hot_cutoff AND recorded_at >= :warm_cutoff
            """
        ),
        {"hot_cutoff": hot_cutoff, "warm_cutoff": warm_cutoff},
    ).scalar_one()
    cold = session.execute(
        text(f"SELECT COUNT(*) FROM {ledger_table} WHERE recorded_at < :warm_cutoff"),
        {"warm_cutoff": warm_cutoff},
    ).scalar_one()
    return int(total), int(hot), int(warm), int(cold)


def run_retention(session: Session, domain: GovernorDomain) -> RetentionReport:
    spec = RETENTION_REGISTRY[domain]
    registry = DOMAIN_REGISTRY[domain]
    if spec.ledger_table != registry.ledger_table:
        raise ValueError(f"retention ledger mismatch for {domain.value}")

    policy = load_retention_policy(session, spec.policy_table)
    now = _utcnow()
    hot_cutoff = now - timedelta(days=policy.hot_days)
    warm_cutoff = now - timedelta(days=policy.warm_days)

    if not _table_exists(session, spec.ledger_table):
        return RetentionReport(
            domain=domain,
            ledger_table=spec.ledger_table,
            total_events=0,
            hot_count=0,
            warm_count=0,
            cold_count=0,
            archived_count=0,
            archive_skipped_reason="ledger_table_missing",
        )

    total, hot, warm, cold = _tier_counts(
        session,
        ledger_table=spec.ledger_table,
        hot_cutoff=hot_cutoff,
        warm_cutoff=warm_cutoff,
    )

    archived = 0
    skip_reason: str | None = None
    if policy.archive_enabled:
        checkpoint_event_id = _load_checkpoint_event_id(session, spec.checkpoint_table)
        if checkpoint_event_id is None:
            skip_reason = "no_verify_checkpoint"
        elif cold == 0:
            skip_reason = "no_cold_tier_events"
        else:
            result = session.execute(
                text(
                    f"""
                    DELETE FROM {spec.ledger_table}
                    WHERE recorded_at < :warm_cutoff
                      AND event_id <= :checkpoint_event_id
                    """
                ),
                {"warm_cutoff": warm_cutoff, "checkpoint_event_id": checkpoint_event_id},
            )
            archived = int(result.rowcount or 0)
    else:
        skip_reason = "archive_disabled"

    return RetentionReport(
        domain=domain,
        ledger_table=spec.ledger_table,
        total_events=total,
        hot_count=hot,
        warm_count=warm,
        cold_count=cold,
        archived_count=archived,
        archive_skipped_reason=skip_reason if archived == 0 else None,
    )
