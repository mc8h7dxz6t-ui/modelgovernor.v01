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
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SIDECAR_PATH) not in sys.path:
    sys.path.insert(0, str(SIDECAR_PATH))

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://localhost:5432/modelgovernor_test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("SIDECAR_INTERNAL_TOKENS", "test-token")

from app.config import get_settings
from app.routes_reserve import reserve
from app.routes_settle import settle
from app.schemas import ReserveRequest, SettleRequest
from fastapi import HTTPException
from reconciler.app.sweeper import sweep_expired_reservations


class MappingResult:
    def __init__(self, rows: list[dict[str, Any]]):
        self._rows = rows

    def first(self) -> dict[str, Any] | None:
        return self._rows[0] if self._rows else None

    def all(self) -> list[dict[str, Any]]:
        return list(self._rows)


class QueryResult:
    def __init__(self, rows: list[Any]):
        self._rows = rows

    def mappings(self) -> MappingResult:
        return MappingResult(self._rows)

    def first(self) -> Any:
        return self._rows[0] if self._rows else None


class FakeSidecarSession:
    def __init__(self, reserve_ttl_seconds: int = 300):
        self.reserve_ttl_seconds = reserve_ttl_seconds
        self.wallets: dict[str, dict[str, Any]] = {
            "demo-user": {"user_id": "demo-user", "balance": Decimal("100.000000"), "active": True}
        }
        self.policies: dict[str, dict[str, Any]] = {
            "gpt-4o-mini": {"enabled": True, "max_cost_per_request": Decimal("5.000000"), "max_cost_per_trace": None}
        }
        self.ledger: dict[str, dict[str, Any]] = {}
        self.ledger_events: list[dict[str, Any]] = []

    def _norm(self, query: Any) -> str:
        return " ".join(str(query).lower().split())

    def execute(self, query: Any, params: dict[str, Any] | None = None) -> QueryResult:
        q = self._norm(query)
        params = params or {}

        if "from escrow_ledger" in q and "where idempotency_key = :idempotency_key" in q and "for update" not in q:
            row = self.ledger.get(params["idempotency_key"])
            return QueryResult([row] if row else [])

        if "from escrow_ledger" in q and "where idempotency_key = :idempotency_key" in q and "for update" in q:
            row = self.ledger.get(params["idempotency_key"])
            return QueryResult([row] if row else [])

        if "from model_policy_registry" in q:
            row = self.policies.get(params["model_name"])
            return QueryResult([row] if row else [])

        if "coalesce(sum(" in q and "from escrow_ledger" in q and "trace_id" in q:
            # Per-trace spend cap aggregation query
            user_id = params["user_id"]
            trace_id = params["trace_id"]
            trace_spend = Decimal("0.000000")
            for row in self.ledger.values():
                if row["user_id"] == user_id and row["trace_id"] == trace_id and row["status"] in ("RESERVED", "SETTLED"):
                    if row["status"] == "RESERVED":
                        trace_spend += row["reserved_amount"]
                    else:
                        trace_spend += row["actual_amount"]
            return QueryResult([{"trace_spend": trace_spend}])

        if "from user_wallets" in q and "for update" in q:
            row = self.wallets.get(params["user_id"])
            return QueryResult([row] if row else [])

        if "insert into escrow_ledger" in q:
            idem = params["idempotency_key"]
            self.ledger[idem] = {
                "idempotency_key": idem,
                "user_id": params["user_id"],
                "trace_id": params["trace_id"],
                "model": params["model"],
                "request_fingerprint": params["request_fingerprint"],
                "reserved_amount": params["reserved_amount"],
                "actual_amount": params["actual_amount"],
                "status": "RESERVED",
                "provider_request_id": None,
                "expires_at": datetime.utcnow() + timedelta(seconds=params["reserve_ttl_seconds"]),
                "expired_at": None,
                "settled_at": None,
            }
            return QueryResult([])

        if "update user_wallets" in q and "set balance = balance -" in q:
            self.wallets[params["user_id"]]["balance"] -= params["reserved_amount"]
            return QueryResult([])

        if "update user_wallets" in q and "set balance = balance +" in q:
            self.wallets[params["user_id"]]["balance"] += params["refund_amount"]
            return QueryResult([])

        if "update escrow_ledger" in q and "set actual_amount" in q:
            row = self.ledger[params["idempotency_key"]]
            row["actual_amount"] = params["actual_amount"]
            row["status"] = "SETTLED"
            row["provider_request_id"] = params["provider_request_id"]
            row["settled_at"] = datetime.utcnow()
            row["expired_at"] = None
            return QueryResult([])

        if "insert into ledger_events" in q:
            self.ledger_events.append(
                {
                    "idempotency_key": params["idempotency_key"],
                    "user_id": params["user_id"],
                    "event_type": "RESERVE_CREATED"
                    if "'reserve_created'" in q
                    else "SETTLED_FINAL"
                    if "'settled_final'" in q
                    else "SETTLEMENT_DRIFT",
                    "amount_delta": params["amount_delta"],
                    "metadata": json.loads(params["metadata"]),
                }
            )
            return QueryResult([])

        raise AssertionError(f"Unexpected SQL: {query}")

    def commit(self) -> None:
        return None

    def rollback(self) -> None:
        return None


class FakeSweeperSession:
    def __init__(self):
        self.wallets: dict[str, dict[str, Any]] = {
            "demo-user": {"user_id": "demo-user", "balance": Decimal("100.000000")}
        }
        self.ledger: dict[str, dict[str, Any]] = {
            "exp-1": {
                "idempotency_key": "exp-1",
                "user_id": "demo-user",
                "reserved_amount": Decimal("3.000000"),
                "status": "RESERVED",
                "expires_at": datetime.utcnow() - timedelta(seconds=5),
                "expired_at": None,
                "settled_at": None,
            },
            "exp-2": {
                "idempotency_key": "exp-2",
                "user_id": "demo-user",
                "reserved_amount": Decimal("2.000000"),
                "status": "RESERVED",
                "expires_at": datetime.utcnow() - timedelta(seconds=2),
                "expired_at": None,
                "settled_at": None,
            },
            "settled": {
                "idempotency_key": "settled",
                "user_id": "demo-user",
                "reserved_amount": Decimal("4.000000"),
                "status": "SETTLED",
                "expires_at": datetime.utcnow() - timedelta(seconds=10),
                "expired_at": None,
                "settled_at": datetime.utcnow() - timedelta(seconds=3),
            },
        }
        self.events: list[dict[str, Any]] = []

    def _norm(self, query: Any) -> str:
        return " ".join(str(query).lower().split())

    @contextmanager
    def begin(self):
        yield self

    def execute(self, query: Any, params: dict[str, Any] | None = None) -> QueryResult:
        q = self._norm(query)
        params = params or {}

        if "for update skip locked" in q and "from escrow_ledger" in q:
            batch_size = params["batch_size"]
            rows = [
                {
                    "idempotency_key": row["idempotency_key"],
                    "user_id": row["user_id"],
                    "reserved_amount": row["reserved_amount"],
                }
                for row in sorted(self.ledger.values(), key=lambda x: (x["expires_at"], x["idempotency_key"]))
                if row["status"] == "RESERVED"
                and row["settled_at"] is None
                and row["expired_at"] is None
                and row["expires_at"] <= datetime.utcnow()
            ][:batch_size]
            return QueryResult(rows)

        if "from user_wallets" in q and "for update" in q:
            row = self.wallets.get(params["user_id"])
            return QueryResult([row] if row else [])

        if "update escrow_ledger" in q and "set status = 'expired'" in q:
            row = self.ledger.get(params["idempotency_key"])
            if row and row["status"] == "RESERVED" and row["settled_at"] is None and row["expired_at"] is None:
                row["status"] = "EXPIRED"
                row["expired_at"] = datetime.utcnow()
                return QueryResult([{"idempotency_key": row["idempotency_key"]}])
            return QueryResult([])

        if "update user_wallets" in q and "set balance = balance +" in q:
            self.wallets[params["user_id"]]["balance"] += params["refund_amount"]
            return QueryResult([])

        if "insert into ledger_events" in q and "'expired_sweep'" in q:
            self.events.append(
                {
                    "idempotency_key": params["idempotency_key"],
                    "user_id": params["user_id"],
                    "event_type": "EXPIRED_SWEEP",
                    "amount_delta": params["amount_delta"],
                    "metadata": json.loads(params["metadata"]),
                }
            )
            return QueryResult([])

        raise AssertionError(f"Unexpected SQL: {query}")


def make_reserve_request(idempotency_key: str = "idem-1", estimated_cost: str = "1.000000") -> ReserveRequest:
    return ReserveRequest(
        user_id="demo-user",
        trace_id=f"trace-{idempotency_key}",
        idempotency_key=idempotency_key,
        model="gpt-4o-mini",
        estimated_cost=Decimal(estimated_cost),
    )


def make_settle_request(
    idempotency_key: str = "idem-1",
    actual_cost: str = "0.500000",
    provider_request_id: str | None = "provider-1",
) -> SettleRequest:
    return SettleRequest(
        idempotency_key=idempotency_key,
        actual_cost=Decimal(actual_cost),
        provider_request_id=provider_request_id,
    )


def configure_env(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://localhost:5432/modelgovernor_test")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("SIDECAR_INTERNAL_TOKENS", "test-token")
    monkeypatch.setenv("RESERVE_TTL_SECONDS", "120")
    get_settings.cache_clear()


def bind_sidecar_session(monkeypatch, session: FakeSidecarSession) -> None:
    @contextmanager
    def fake_db_session():
        yield session

    monkeypatch.setattr("app.routes_reserve.get_db_session", fake_db_session)
    monkeypatch.setattr("app.routes_settle.get_db_session", fake_db_session)


def test_duplicate_reserve_replay(monkeypatch) -> None:
    configure_env(monkeypatch)
    session = FakeSidecarSession(reserve_ttl_seconds=120)
    bind_sidecar_session(monkeypatch, session)

    first = reserve(make_reserve_request(idempotency_key="r1", estimated_cost="1.000000"))
    replay = reserve(make_reserve_request(idempotency_key="r1", estimated_cost="1.000000"))

    assert first.status == "RESERVED"
    assert replay.status == "RESERVED"
    assert len(session.ledger) == 1
    assert len([e for e in session.ledger_events if e["event_type"] == "RESERVE_CREATED"]) == 1


def test_conflicting_reserve_replay(monkeypatch) -> None:
    configure_env(monkeypatch)
    session = FakeSidecarSession()
    bind_sidecar_session(monkeypatch, session)

    reserve(make_reserve_request(idempotency_key="r2", estimated_cost="1.000000"))

    try:
        reserve(make_reserve_request(idempotency_key="r2", estimated_cost="2.000000"))
        raise AssertionError("Expected reserve replay conflict")
    except HTTPException as exc:
        assert exc.status_code == 409


def test_insufficient_funds(monkeypatch) -> None:
    configure_env(monkeypatch)
    session = FakeSidecarSession()
    session.wallets["demo-user"]["balance"] = Decimal("0.500000")
    bind_sidecar_session(monkeypatch, session)

    try:
        reserve(make_reserve_request(idempotency_key="r3", estimated_cost="1.000000"))
        raise AssertionError("Expected insufficient funds conflict")
    except HTTPException as exc:
        assert exc.status_code == 409


def test_successful_settle(monkeypatch) -> None:
    configure_env(monkeypatch)
    session = FakeSidecarSession()
    bind_sidecar_session(monkeypatch, session)

    reserve(make_reserve_request(idempotency_key="r4", estimated_cost="1.000000"))
    result = settle(make_settle_request(idempotency_key="r4", actual_cost="0.500000", provider_request_id="p-4"))

    assert result.status == "SETTLED"
    assert result.actual_amount == Decimal("0.500000")
    assert session.ledger["r4"]["status"] == "SETTLED"
    assert session.wallets["demo-user"]["balance"] == Decimal("99.500000")
    settled_event = [e for e in session.ledger_events if e["event_type"] == "SETTLED_FINAL"][0]
    assert settled_event["metadata"]["provider_request_id"] == "p-4"
    assert settled_event["metadata"]["actual_amount"] == "0.500000"


def test_duplicate_settle_replay(monkeypatch) -> None:
    configure_env(monkeypatch)
    session = FakeSidecarSession()
    bind_sidecar_session(monkeypatch, session)

    reserve(make_reserve_request(idempotency_key="r5", estimated_cost="1.000000"))
    first = settle(make_settle_request(idempotency_key="r5", actual_cost="0.500000", provider_request_id="p-5"))
    replay = settle(make_settle_request(idempotency_key="r5", actual_cost="0.500000", provider_request_id="p-5"))

    assert first.status == "SETTLED"
    assert replay.status == "SETTLED"
    assert len([e for e in session.ledger_events if e["event_type"] == "SETTLED_FINAL"]) == 1


def test_conflicting_settle_replay(monkeypatch) -> None:
    configure_env(monkeypatch)
    session = FakeSidecarSession()
    bind_sidecar_session(monkeypatch, session)

    reserve(make_reserve_request(idempotency_key="r6", estimated_cost="1.000000"))
    settle(make_settle_request(idempotency_key="r6", actual_cost="0.500000", provider_request_id="p-6"))

    try:
        settle(make_settle_request(idempotency_key="r6", actual_cost="0.600000", provider_request_id="p-6"))
        raise AssertionError("Expected settle replay conflict")
    except HTTPException as exc:
        assert exc.status_code == 409


def test_expired_cannot_settle(monkeypatch) -> None:
    configure_env(monkeypatch)
    session = FakeSidecarSession()
    bind_sidecar_session(monkeypatch, session)

    reserve(make_reserve_request(idempotency_key="r7", estimated_cost="1.000000"))
    session.ledger["r7"]["status"] = "EXPIRED"
    session.ledger["r7"]["expired_at"] = datetime.utcnow()

    try:
        settle(make_settle_request(idempotency_key="r7", actual_cost="0.500000", provider_request_id="p-7"))
        raise AssertionError("Expected expired reservation to reject settlement")
    except HTTPException as exc:
        assert exc.status_code == 409


def test_sweeper_refund_path() -> None:
    session = FakeSweeperSession()
    swept = sweep_expired_reservations(session, batch_size=1)

    assert swept == 2
    assert session.ledger["exp-1"]["status"] == "EXPIRED"
    assert session.ledger["exp-2"]["status"] == "EXPIRED"
    assert session.ledger["settled"]["status"] == "SETTLED"
    assert len(session.events) == 2
    assert all(event["event_type"] == "EXPIRED_SWEEP" for event in session.events)


def test_balance_invariants(monkeypatch) -> None:
    configure_env(monkeypatch)
    session = FakeSidecarSession()
    bind_sidecar_session(monkeypatch, session)

    starting_balance = session.wallets["demo-user"]["balance"]
    reserve(make_reserve_request(idempotency_key="r8", estimated_cost="1.000000"))
    settle(make_settle_request(idempotency_key="r8", actual_cost="0.400000", provider_request_id="p-8"))

    reserve(make_reserve_request(idempotency_key="r9", estimated_cost="2.000000"))
    session.ledger["r9"]["expires_at"] = datetime.utcnow() - timedelta(seconds=10)

    sweep_session = FakeSweeperSession()
    sweep_session.wallets["demo-user"]["balance"] = session.wallets["demo-user"]["balance"]
    sweep_session.ledger = {
        "r9": {
            "idempotency_key": "r9",
            "user_id": "demo-user",
            "reserved_amount": session.ledger["r9"]["reserved_amount"],
            "status": "RESERVED",
            "expires_at": session.ledger["r9"]["expires_at"],
            "expired_at": None,
            "settled_at": None,
        }
    }
    sweep_session.events = []

    swept = sweep_expired_reservations(sweep_session, batch_size=10)
    assert swept == 1

    net_actual = Decimal("0.400000")
    pending_reserved = session.ledger["r9"]["reserved_amount"]
    expected_before_r9_refund = starting_balance - net_actual - pending_reserved
    assert session.wallets["demo-user"]["balance"] == expected_before_r9_refund

    assert sweep_session.wallets["demo-user"]["balance"] == session.wallets["demo-user"]["balance"] + session.ledger["r9"]["reserved_amount"]
    assert sweep_session.ledger["r9"]["status"] == "EXPIRED"
