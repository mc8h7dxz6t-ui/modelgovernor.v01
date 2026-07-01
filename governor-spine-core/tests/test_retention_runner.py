"""K4 — retention runner unit tests."""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.orm import Session

from spine_core.config import GovernorDomain
from spine_core.retention_runner import RETENTION_REGISTRY, load_retention_policy, run_retention

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def test_k4_all_four_governors_registered():
    assert len(RETENTION_REGISTRY) == 4


def test_retention_report_archive_disabled(tmp_path) -> None:
    from tests.integration.test_ledger_hardening import _bootstrap_schema, _create_test_engine

    engine = _create_test_engine(tmp_path / "retention.sqlite3")
    _bootstrap_schema(engine)
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS ledger_events_retention_policy (
                    policy_id VARCHAR(64) PRIMARY KEY,
                    hot_days INT NOT NULL DEFAULT 90,
                    warm_days INT NOT NULL DEFAULT 365,
                    archive_enabled BOOLEAN NOT NULL DEFAULT FALSE,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO ledger_events_retention_policy
                (policy_id, hot_days, warm_days, archive_enabled)
                VALUES ('default', 90, 365, 0)
                """
            )
        )
        old = (datetime.now(timezone.utc) - timedelta(days=400)).isoformat()
        connection.execute(
            text(
                """
                INSERT INTO ledger_events
                (idempotency_key, user_id, event_type, amount_delta, metadata, recorded_at)
                VALUES ('old-1', 'user-1', 'RESERVED', 1.0, '{}', :recorded_at)
                """
            ),
            {"recorded_at": old},
        )

    with Session(engine) as session:
        policy = load_retention_policy(session, "ledger_events_retention_policy")
        assert policy.archive_enabled is False
        report = run_retention(session, GovernorDomain.MODEL)
        assert report.total_events == 1
        assert report.cold_count == 1
        assert report.archived_count == 0
        assert report.archive_skipped_reason == "archive_disabled"
