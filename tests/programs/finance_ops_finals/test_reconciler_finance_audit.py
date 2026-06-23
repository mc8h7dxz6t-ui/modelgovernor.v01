"""Reconciler post-sweep finance audit tests."""
from __future__ import annotations

from decimal import Decimal
from pathlib import Path
import sys

from sqlalchemy.orm import sessionmaker

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from reconciler.app.main import _run_finance_audit
from sidecar.app.config import Settings
from sidecar.app.ledger import reserve_operation
from sidecar.app.schemas import ReserveRequest
from tests.integration.test_ledger_hardening import _bootstrap_schema, _create_test_engine, _seed_wallet_and_model


def test_finance_audit_passes_on_clean_ledger(tmp_path) -> None:
    engine = _create_test_engine(tmp_path / "audit.sqlite3")
    _bootstrap_schema(engine)
    _seed_wallet_and_model(engine, user_id="audit-user", balance=Decimal("50"))
    settings = Settings(
        database_url=str(engine.url),
        redis_url="redis://example/0",
        sidecar_internal_tokens="token",
    )
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

    with factory() as session:
        reserve_operation(
            session,
            settings,
            ReserveRequest(
                user_id="audit-user",
                trace_id="audit-trace",
                idempotency_key="audit-op",
                model="gpt-4o-mini",
                estimated_cost=Decimal("5"),
            ),
        )

    with factory() as session:
        _run_finance_audit(session)
