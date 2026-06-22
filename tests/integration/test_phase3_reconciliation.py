"""
Phase 3 integration tests — provider reconciliation and admin correction coverage.
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timedelta
from decimal import Decimal
import json
import os
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
SIDECAR_PATH = ROOT / "sidecar"
for p in (str(ROOT), str(SIDECAR_PATH)):
    if p not in sys.path:
        sys.path.insert(0, p)

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://localhost:5432/modelgovernor_test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("SIDECAR_INTERNAL_TOKENS", "test-token")

from app.config import get_settings
from app.routes_reconcile import apply_provider_adjustment, reconcile_provider
from app.schemas import ProviderAdjustmentRequest, ProviderReconciliationRequest
from fastapi import HTTPException


class MappingResult:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self._rows = rows

    def first(self) -> dict[str, Any] | None:
        return self._rows[0] if self._rows else None

    def all(self) -> list[dict[str, Any]]:
        return list(self._rows)


class QueryResult:
    def __init__(self, rows: list[Any]) -> None:
        self._rows = rows

    def mappings(self) -> MappingResult:
        return MappingResult(self._rows)

    def first(self) -> Any:
        return self._rows[0] if self._rows else None


class FakePhase3Session:
    def __init__(self) -> None:
        self.wallets: dict[str, dict[str, Any]] = {
            "demo-user": {"user_id": "demo-user", "balance": Decimal("5.000000"), "active": True}
        }
        self.ledger: dict[str, dict[str, Any]] = {
            "settled-1": {
                "idempotency_key": "settled-1",
                "user_id": "demo-user",
                "actual_amount": Decimal("0.800000"),
                "status": "SETTLED",
                "provider_request_id": "prov-1",
                "reconciled": False,
                "expires_at": datetime.utcnow() + timedelta(seconds=60),
            }
        }
        self.provider_reconciliations: dict[str, dict[str, Any]] = {}
        self.provider_adjustments: dict[str, dict[str, Any]] = {}
        self.ledger_events: list[dict[str, Any]] = []

    def _norm(self, query: Any) -> str:
        return " ".join(str(query).lower().split())

    def execute(self, query: Any, params: dict[str, Any] | None = None) -> QueryResult:
        q = self._norm(query)
        params = params or {}

        if "from provider_reconciliations" in q and "where reconciliation_key = :reconciliation_key" in q:
            row = self.provider_reconciliations.get(params["reconciliation_key"])
            return QueryResult([row] if row else [])

        if "from provider_adjustments" in q and "where adjustment_key = :adjustment_key" in q:
            row = self.provider_adjustments.get(params["adjustment_key"])
            return QueryResult([row] if row else [])

        if "from escrow_ledger" in q and "where idempotency_key = :idempotency_key" in q:
            row = self.ledger.get(params["idempotency_key"])
            return QueryResult([row] if row else [])

        if "from escrow_ledger" in q and "where provider_request_id = :provider_request_id" in q:
            row = next(
                (candidate for candidate in self.ledger.values() if candidate["provider_request_id"] == params["provider_request_id"]),
                None,
            )
            return QueryResult([row] if row else [])

        if "from user_wallets" in q and "for update" in q:
            row = self.wallets.get(params["user_id"])
            return QueryResult([row] if row else [])

        if "insert into provider_reconciliations" in q:
            self.provider_reconciliations[params["reconciliation_key"]] = {
                "reconciliation_key": params["reconciliation_key"],
                "idempotency_key": params["idempotency_key"],
                "provider": params["provider"],
                "provider_request_id": params["provider_request_id"],
                "provider_actual_amount": params["provider_actual_amount"],
                "ledger_actual_amount": params["ledger_actual_amount"],
                "discrepancy_amount": params["discrepancy_amount"],
                "status": params["status"],
                "external_reference": params["external_reference"],
            }
            return QueryResult([])

        if "update escrow_ledger" in q and "set reconciled = true" in q and "actual_amount" not in q:
            row = self.ledger[params["idempotency_key"]]
            row["reconciled"] = True
            return QueryResult([])

        if "update escrow_ledger" in q and "set actual_amount = :actual_amount" in q:
            row = self.ledger[params["idempotency_key"]]
            row["actual_amount"] = params["actual_amount"]
            row["reconciled"] = True
            return QueryResult([])

        if "update user_wallets" in q and "set balance = balance + :wallet_delta" in q:
            self.wallets[params["user_id"]]["balance"] += params["wallet_delta"]
            return QueryResult([])

        if "update provider_reconciliations" in q and "set status = 'resolved'" in q:
            row = self.provider_reconciliations[params["reconciliation_key"]]
            row["status"] = "RESOLVED"
            row["resolved_at"] = datetime.utcnow()
            return QueryResult([])

        if "insert into provider_adjustments" in q:
            self.provider_adjustments[params["adjustment_key"]] = {
                "adjustment_key": params["adjustment_key"],
                "reconciliation_key": params["reconciliation_key"],
                "idempotency_key": params["idempotency_key"],
                "corrected_actual_amount": params["corrected_actual_amount"],
                "wallet_delta": params["wallet_delta"],
                "reason": params["reason"],
            }
            return QueryResult([])

        if "insert into ledger_events" in q:
            if "'provider_reconciled'" in q:
                event_type = "PROVIDER_RECONCILED"
            else:
                event_type = "PROVIDER_ADJUSTMENT"
            self.ledger_events.append(
                {
                    "idempotency_key": params["idempotency_key"],
                    "user_id": params["user_id"],
                    "event_type": event_type,
                    "amount_delta": params["amount_delta"],
                    "metadata": json.loads(params["metadata"]),
                }
            )
            return QueryResult([])

        raise AssertionError(f"Unexpected SQL: {query}")

    def commit(self) -> None:
        return None


def configure_env(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://localhost:5432/modelgovernor_test")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("SIDECAR_INTERNAL_TOKENS", "test-token")
    get_settings.cache_clear()


def bind_session(monkeypatch, session: FakePhase3Session) -> None:
    @contextmanager
    def _fake_get_db_session():
        yield session

    monkeypatch.setattr("app.routes_reconcile.get_db_session", _fake_get_db_session)


def make_reconciliation_request(
    *,
    reconciliation_key: str = "recon-1",
    provider: str = "openai",
    idempotency_key: str | None = "settled-1",
    provider_request_id: str | None = None,
    provider_actual_cost: str = "0.800000",
    external_reference: str | None = None,
) -> ProviderReconciliationRequest:
    return ProviderReconciliationRequest(
        reconciliation_key=reconciliation_key,
        provider=provider,
        idempotency_key=idempotency_key,
        provider_request_id=provider_request_id,
        provider_actual_cost=Decimal(provider_actual_cost),
        external_reference=external_reference,
    )


def make_adjustment_request(
    *,
    adjustment_key: str = "adj-1",
    reconciliation_key: str = "recon-1",
    reason: str = "provider settlement correction",
) -> ProviderAdjustmentRequest:
    return ProviderAdjustmentRequest(
        adjustment_key=adjustment_key,
        reconciliation_key=reconciliation_key,
        reason=reason,
    )


def test_provider_reconciliation_records_matched_result(monkeypatch) -> None:
    configure_env(monkeypatch)
    session = FakePhase3Session()
    bind_session(monkeypatch, session)

    result = reconcile_provider(make_reconciliation_request())

    assert result.status == "MATCHED"
    assert result.discrepancy_amount == Decimal("0.000000")
    assert session.ledger["settled-1"]["reconciled"] is True
    assert session.provider_reconciliations["recon-1"]["status"] == "MATCHED"
    assert session.ledger_events[-1]["event_type"] == "PROVIDER_RECONCILED"


def test_provider_reconciliation_by_provider_request_id_surfaces_discrepancy(monkeypatch) -> None:
    configure_env(monkeypatch)
    session = FakePhase3Session()
    bind_session(monkeypatch, session)

    result = reconcile_provider(
        make_reconciliation_request(
            reconciliation_key="recon-2",
            idempotency_key=None,
            provider_request_id="prov-1",
            provider_actual_cost="1.100000",
        )
    )

    assert result.status == "MISMATCHED"
    assert result.discrepancy_amount == Decimal("0.300000")
    assert session.provider_reconciliations["recon-2"]["provider_request_id"] == "prov-1"
    assert session.ledger_events[-1]["amount_delta"] == Decimal("0.300000")


def test_provider_reconciliation_replay_is_idempotent(monkeypatch) -> None:
    configure_env(monkeypatch)
    session = FakePhase3Session()
    bind_session(monkeypatch, session)

    first = reconcile_provider(make_reconciliation_request(reconciliation_key="recon-3"))
    event_count = len(session.ledger_events)
    replay = reconcile_provider(make_reconciliation_request(reconciliation_key="recon-3"))

    assert first == replay
    assert len(session.ledger_events) == event_count


def test_provider_reconciliation_replay_rejects_conflicting_parameters(monkeypatch) -> None:
    configure_env(monkeypatch)
    session = FakePhase3Session()
    bind_session(monkeypatch, session)

    reconcile_provider(make_reconciliation_request(reconciliation_key="recon-4"))

    try:
        reconcile_provider(make_reconciliation_request(reconciliation_key="recon-4", provider_actual_cost="1.000000"))
    except HTTPException as exc:
        assert exc.status_code == 409
        assert "reconciliation_key already exists" in str(exc.detail)
    else:
        raise AssertionError("expected conflicting reconciliation replay to fail")


def test_provider_adjustment_resolves_discrepancy_and_updates_wallet(monkeypatch) -> None:
    configure_env(monkeypatch)
    session = FakePhase3Session()
    bind_session(monkeypatch, session)
    reconcile_provider(make_reconciliation_request(reconciliation_key="recon-5", provider_actual_cost="1.100000"))

    result = apply_provider_adjustment(make_adjustment_request(adjustment_key="adj-5", reconciliation_key="recon-5"))

    assert result.status == "RESOLVED"
    assert result.corrected_actual_amount == Decimal("1.100000")
    assert result.wallet_delta == Decimal("-0.300000")
    assert session.wallets["demo-user"]["balance"] == Decimal("4.700000")
    assert session.ledger["settled-1"]["actual_amount"] == Decimal("1.100000")
    assert session.provider_reconciliations["recon-5"]["status"] == "RESOLVED"
    assert session.ledger_events[-1]["event_type"] == "PROVIDER_ADJUSTMENT"


def test_provider_adjustment_replay_is_idempotent(monkeypatch) -> None:
    configure_env(monkeypatch)
    session = FakePhase3Session()
    bind_session(monkeypatch, session)
    reconcile_provider(make_reconciliation_request(reconciliation_key="recon-6", provider_actual_cost="0.600000"))

    first = apply_provider_adjustment(make_adjustment_request(adjustment_key="adj-6", reconciliation_key="recon-6"))
    wallet_balance = session.wallets["demo-user"]["balance"]
    event_count = len(session.ledger_events)
    replay = apply_provider_adjustment(make_adjustment_request(adjustment_key="adj-6", reconciliation_key="recon-6"))

    assert first == replay
    assert session.wallets["demo-user"]["balance"] == wallet_balance
    assert len(session.ledger_events) == event_count


def test_provider_adjustment_rejects_insufficient_balance(monkeypatch) -> None:
    configure_env(monkeypatch)
    session = FakePhase3Session()
    session.wallets["demo-user"]["balance"] = Decimal("0.050000")
    bind_session(monkeypatch, session)
    reconcile_provider(make_reconciliation_request(reconciliation_key="recon-7", provider_actual_cost="1.100000"))

    try:
        apply_provider_adjustment(make_adjustment_request(adjustment_key="adj-7", reconciliation_key="recon-7"))
    except HTTPException as exc:
        assert exc.status_code == 409
        assert "insufficient wallet balance" in str(exc.detail)
    else:
        raise AssertionError("expected insufficient-balance adjustment to fail")
