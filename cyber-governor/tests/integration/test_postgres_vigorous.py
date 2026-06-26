"""Tier 2 — Postgres vigorous institutional++ tests."""
from __future__ import annotations

import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

ROOT = Path(__file__).resolve().parents[2]
SIDECAR = ROOT / "spine" / "sidecar"
sys.path.insert(0, str(SIDECAR))

from tests.helpers import identity_facets

pytestmark = [pytest.mark.usefixtures("clean_cg_tables")]


def _session_maker(engine: Engine):
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


class TestPostgresHappyPath:
    def test_crystallize_commit_jsonb_and_enum(self, pg_engine, pg_settings, monkeypatch):
        from app.config import Settings, get_settings
        from app.db import override_engine
        from app.main import app

        override_engine(pg_engine)
        test_settings = Settings(
            database_url=str(pg_engine.url),
            redis_url="redis://localhost:6390/0",
            cg_internal_tokens="test-token",
        )
        monkeypatch.setattr("app.config.get_settings", lambda: test_settings)
        monkeypatch.setattr("app.auth_oidc.get_settings", lambda: test_settings)

        client = TestClient(app)
        headers = {"x-internal-token": "test-token"}
        facets = identity_facets(policy_version="v12")
        cr = client.post(
            "/crystallize",
            headers=headers,
            json={
                "platform": "identity_gate",
                "operation_id": "pg-happy-1",
                "account_id": "tenant-default",
                "risk_tier": "critical",
                "facets": facets,
                "policy_id": "identity-critical-us",
            },
        )
        assert cr.status_code == 200, cr.text
        crystal_id = cr.json()["crystal_id"]
        cm = client.post(
            "/commit",
            headers=headers,
            json={"crystal_id": crystal_id, "facets": facets, "outcome": "authorized"},
        )
        assert cm.status_code == 200
        assert cm.json()["status"] == "COMMITTED"

        with pg_engine.connect() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT facets, status FROM threat_crystals c
                    JOIN action_escrow_ledger e ON e.crystal_id = c.crystal_id
                    WHERE c.crystal_id = :cid
                    """
                ),
                {"cid": crystal_id},
            ).mappings().first()
            assert row["status"] == "COMMITTED"
            facets_db = row["facets"]
            if isinstance(facets_db, str):
                facets_db = json.loads(facets_db)
            assert facets_db.get("policy_version") == "v12"

        verify = client.get("/internal/security/verify-chain", headers=headers)
        assert verify.status_code == 200
        anchor = client.post("/internal/security/anchor-head", headers=headers)
        assert anchor.status_code == 200
        assert anchor.json()["anchored"] is True


class TestPostgresConstraints:
    def test_negative_balance_check_constraint(self, pg_engine):
        with pg_engine.begin() as conn:
            with pytest.raises(Exception):
                conn.execute(
                    text(
                        """
                        UPDATE principal_budgets SET balance = -1
                        WHERE account_id = 'tenant-default'
                        """
                    )
                )

    def test_action_cap_check_constraint(self, pg_engine):
        with pg_engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO action_budget_state (scope_key, cap_amount, reserved_total)
                    VALUES ('desk/test', 100, 0)
                    """
                )
            )
            with pytest.raises(Exception):
                conn.execute(
                    text(
                        """
                        UPDATE action_budget_state SET reserved_total = 200
                        WHERE scope_key = 'desk/test'
                        """
                    )
                )


class TestPostgresConcurrency:
    def test_concurrent_horizon_sweep_skip_locked(self, pg_engine, pg_settings):
        from app.db import override_engine
        from app.horizon_sweep import sweep_expired_horizons

        override_engine(pg_engine)
        horizon = datetime.now(timezone.utc) - timedelta(minutes=5)
        Session = _session_maker(pg_engine)
        with Session() as s:
            s.execute(
                text(
                    """
                    INSERT INTO threat_crystals (
                        crystal_id, platform, operation_id, risk_tier, facets,
                        request_fingerprint, crystal_hash, horizon_expires_at
                    ) VALUES (
                        'tcrys_conc', 'identity_gate', 'op-conc', 'critical', '{}',
                        'fp', 'h1', :horizon
                    )
                    """
                ),
                {"horizon": horizon},
            )
            s.execute(
                text(
                    """
                    INSERT INTO action_escrow_ledger (
                        operation_id, crystal_id, account_id, platform,
                        reserved_exposure, status, expires_at
                    ) VALUES (
                        'op-conc', 'tcrys_conc', 'tenant-default', 'identity_gate',
                        0, 'CRYSTALLIZED', :horizon
                    )
                    """
                ),
                {"horizon": horizon},
            )
            s.commit()

        def _sweep() -> int:
            with Session() as session:
                return sweep_expired_horizons(session, batch_size=10)

        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(lambda _: _sweep(), range(4)))

        assert sum(results) == 1
        with pg_engine.connect() as conn:
            state = conn.execute(
                text("SELECT terminal_state FROM threat_crystals WHERE crystal_id = 'tcrys_conc'")
            ).scalar_one()
            assert state == "STRANDED"
            events = conn.execute(
                text(
                    """
                    SELECT COUNT(*) FROM security_events
                    WHERE crystal_id = 'tcrys_conc' AND event_type = 'STRANDED_HOLD'
                    """
                )
            ).scalar_one()
            assert events == 1

    def test_concurrent_crystallize_same_operation_id(self, pg_engine, pg_settings):
        from app.commit_ledger import crystallize_operation
        from app.db import override_engine

        override_engine(pg_engine)
        facets = identity_facets()
        Session = _session_maker(pg_engine)
        crystal_ids: list[str] = []

        def _crystallize() -> str:
            with Session() as s:
                result = crystallize_operation(
                    s,
                    pg_settings,
                    platform="identity_gate",
                    operation_id="pg-concurrent-op",
                    account_id="tenant-default",
                    risk_tier="critical",
                    facets=facets,
                )
                return result.crystal_id

        with ThreadPoolExecutor(max_workers=8) as pool:
            futures = [pool.submit(_crystallize) for _ in range(8)]
            crystal_ids = [f.result() for f in as_completed(futures)]

        assert len(set(crystal_ids)) == 1


class TestPostgresLineage:
    def test_lineage_ingest_persists_edges(self, pg_engine, monkeypatch):
        from app.config import Settings
        from app.db import override_engine
        from app.main import app

        override_engine(pg_engine)
        test_settings = Settings(
            database_url=str(pg_engine.url),
            redis_url="redis://localhost:6390/0",
            cg_internal_tokens="test-token",
            oidc_enabled=False,
        )
        monkeypatch.setattr("app.config.get_settings", lambda: test_settings)
        monkeypatch.setattr("app.auth_oidc.get_settings", lambda: test_settings)
        client = TestClient(app)
        headers = {"x-internal-token": "test-token"}
        r = client.post(
            "/internal/lineage/ingest",
            headers=headers,
            json={
                "source": "tetragon",
                "payload": {
                    "process_connect": {
                        "process": {"exec_id": "e1", "binary": "/bin/curl", "pod": {"name": "payments"}},
                        "socket": {"address": "203.0.113.1:443"},
                    }
                },
            },
        )
        assert r.status_code == 200
        dag = client.get("/internal/lineage/dag/payments", headers=headers)
        assert len(dag.json()) >= 1
