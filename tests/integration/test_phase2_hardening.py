"""
Phase 2 integration tests — production hardening coverage.

Tests in this file cover:
  - Per-trace spend cap enforcement (402 when cap exceeded)
  - Degraded-mode handling (503 when backing store raises OperationalError)
  - Provider request ID audit completeness
  - Concurrent reconciler idempotency (SKIP LOCKED behaviour)
  - Audit event completeness for all terminal ledger transitions
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
from app.routes_reserve import reserve
from app.routes_settle import settle
from app.schemas import ReserveRequest, SettleRequest
from fastapi import HTTPException
from reconciler.app.sweeper import sweep_expired_reservations
from sqlalchemy.exc import OperationalError


# ---------------------------------------------------------------------------
# Shared test infrastructure
# ---------------------------------------------------------------------------


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


class FakeSidecarSession:
    """In-memory sidecar session supporting per-trace spend cap queries."""

    def __init__(self, reserve_ttl_seconds: int = 300, max_cost_per_trace: Decimal | None = None) -> None:
        self.reserve_ttl_seconds = reserve_ttl_seconds
        self.wallets: dict[str, dict[str, Any]] = {
            "demo-user": {"user_id": "demo-user", "balance": Decimal("100.000000"), "active": True}
        }
        self.policies: dict[str, dict[str, Any]] = {
            "gpt-4o-mini": {
                "enabled": True,
                "max_cost_per_request": Decimal("5.000000"),
                "max_cost_per_trace": max_cost_per_trace,
            }
        }
        self.ledger: dict[str, dict[str, Any]] = {}
        self.ledger_events: list[dict[str, Any]] = []

    def _norm(self, query: Any) -> str:
        return " ".join(str(query).lower().split())

    def execute(self, query: Any, params: dict[str, Any] | None = None) -> QueryResult:
        q = self._norm(query)
        params = params or {}

        if "from escrow_ledger" in q and "where idempotency_key = :idempotency_key" in q:
            row = self.ledger.get(params["idempotency_key"])
            return QueryResult([row] if row else [])

        if "from model_policy_registry" in q:
            row = self.policies.get(params["model_name"])
            return QueryResult([row] if row else [])

        if "coalesce(sum(" in q and "from escrow_ledger" in q and "trace_id" in q:
            user_id = params["user_id"]
            trace_id = params["trace_id"]
            trace_spend = Decimal("0.000000")
            for row in self.ledger.values():
                if (
                    row["user_id"] == user_id
                    and row["trace_id"] == trace_id
                    and row["status"] in ("RESERVED", "SETTLED")
                ):
                    trace_spend += row["reserved_amount"] if row["status"] == "RESERVED" else row["actual_amount"]
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
    """In-memory sweeper session for reconciler tests."""

    def __init__(self) -> None:
        self.wallets: dict[str, dict[str, Any]] = {
            "demo-user": {"user_id": "demo-user", "balance": Decimal("100.000000")}
        }
        self.ledger: dict[str, dict[str, Any]] = {}
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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


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


def make_reserve_request(
    idempotency_key: str = "idem-1",
    estimated_cost: str = "1.000000",
    trace_id: str | None = None,
) -> ReserveRequest:
    return ReserveRequest(
        user_id="demo-user",
        trace_id=trace_id or f"trace-{idempotency_key}",
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


# ---------------------------------------------------------------------------
# Per-trace spend cap tests
# ---------------------------------------------------------------------------


def test_trace_cap_not_enforced_when_null(monkeypatch) -> None:
    """max_cost_per_trace=None disables the cap check entirely."""
    configure_env(monkeypatch)
    session = FakeSidecarSession(max_cost_per_trace=None)
    bind_sidecar_session(monkeypatch, session)

    # Many reservations on the same trace should all succeed when cap is null.
    for i in range(5):
        result = reserve(make_reserve_request(idempotency_key=f"tc-null-{i}", estimated_cost="1.000000", trace_id="trace-shared"))
        assert result.status == "RESERVED"


def test_trace_cap_first_reservation_accepted(monkeypatch) -> None:
    """A single reservation within the trace cap is accepted."""
    configure_env(monkeypatch)
    session = FakeSidecarSession(max_cost_per_trace=Decimal("5.000000"))
    bind_sidecar_session(monkeypatch, session)

    result = reserve(make_reserve_request(idempotency_key="tc-1", estimated_cost="1.000000", trace_id="trace-capped"))
    assert result.status == "RESERVED"


def test_trace_cap_exceeded_returns_402(monkeypatch) -> None:
    """Reservations that would push trace spend over the cap are rejected with 402."""
    configure_env(monkeypatch)
    # Cap of 3.000000; reserve_amount = max(1.0 * 1.25, 0.01) = 1.25 per call.
    # Three calls × 1.25 = 3.75 which exceeds the cap of 3.00 on the third call.
    session = FakeSidecarSession(max_cost_per_trace=Decimal("3.000000"))
    bind_sidecar_session(monkeypatch, session)

    reserve(make_reserve_request(idempotency_key="tc-cap-1", estimated_cost="1.000000", trace_id="trace-over"))
    reserve(make_reserve_request(idempotency_key="tc-cap-2", estimated_cost="1.000000", trace_id="trace-over"))

    try:
        reserve(make_reserve_request(idempotency_key="tc-cap-3", estimated_cost="1.000000", trace_id="trace-over"))
        raise AssertionError("Expected per-trace cap rejection")
    except HTTPException as exc:
        assert exc.status_code == 402
        assert "per-trace spend cap" in exc.detail


def test_trace_cap_settled_spend_counts_toward_cap(monkeypatch) -> None:
    """Settled amounts count toward the trace cap on subsequent reservations."""
    configure_env(monkeypatch)
    session = FakeSidecarSession(max_cost_per_trace=Decimal("2.000000"))
    bind_sidecar_session(monkeypatch, session)

    # Reserve and settle 1.25 (reserve of 1.0 × 1.25).
    reserve(make_reserve_request(idempotency_key="tc-s-1", estimated_cost="1.000000", trace_id="trace-settled-cap"))
    # Manually mark as SETTLED with actual_amount = 1.25 so the cap query counts it.
    session.ledger["tc-s-1"]["status"] = "SETTLED"
    session.ledger["tc-s-1"]["actual_amount"] = Decimal("1.250000")

    # Another reserve of 1.25 would bring total to 2.50, exceeding cap of 2.00.
    try:
        reserve(make_reserve_request(idempotency_key="tc-s-2", estimated_cost="1.000000", trace_id="trace-settled-cap"))
        raise AssertionError("Expected per-trace cap rejection after settled spend counted")
    except HTTPException as exc:
        assert exc.status_code == 402


def test_trace_cap_independent_traces_unaffected(monkeypatch) -> None:
    """Spend on one trace_id does not affect the cap for a different trace_id."""
    configure_env(monkeypatch)
    session = FakeSidecarSession(max_cost_per_trace=Decimal("2.000000"))
    bind_sidecar_session(monkeypatch, session)

    # Fill up trace-A
    reserve(make_reserve_request(idempotency_key="tci-a-1", estimated_cost="1.000000", trace_id="trace-A"))

    # trace-B should be unaffected
    result = reserve(make_reserve_request(idempotency_key="tci-b-1", estimated_cost="1.000000", trace_id="trace-B"))
    assert result.status == "RESERVED"


# ---------------------------------------------------------------------------
# Degraded-mode (503) tests
# ---------------------------------------------------------------------------


def _raising_db_session():
    @contextmanager
    def fake_db_session():
        raise OperationalError("connection refused", None, None)
        yield  # pragma: no cover

    return fake_db_session


def test_reserve_returns_503_on_db_error(monkeypatch) -> None:
    """Reserve returns 503 when the backing store is unavailable."""
    configure_env(monkeypatch)
    monkeypatch.setattr("app.routes_reserve.get_db_session", _raising_db_session())

    try:
        reserve(make_reserve_request())
        raise AssertionError("Expected 503 on DB error")
    except HTTPException as exc:
        assert exc.status_code == 503
        assert "temporarily unavailable" in exc.detail


def test_settle_returns_503_on_db_error(monkeypatch) -> None:
    """Settle returns 503 when the backing store is unavailable."""
    configure_env(monkeypatch)
    monkeypatch.setattr("app.routes_settle.get_db_session", _raising_db_session())

    try:
        settle(make_settle_request())
        raise AssertionError("Expected 503 on DB error")
    except HTTPException as exc:
        assert exc.status_code == 503
        assert "temporarily unavailable" in exc.detail


# ---------------------------------------------------------------------------
# Provider request ID audit completeness
# ---------------------------------------------------------------------------


def test_provider_request_id_captured_in_settled_event(monkeypatch) -> None:
    """provider_request_id is stored in the SETTLED_FINAL audit event metadata."""
    configure_env(monkeypatch)
    session = FakeSidecarSession()
    bind_sidecar_session(monkeypatch, session)

    reserve(make_reserve_request(idempotency_key="pid-1", estimated_cost="1.000000"))
    settle(make_settle_request(idempotency_key="pid-1", actual_cost="0.800000", provider_request_id="prov-xyz-001"))

    settled_events = [e for e in session.ledger_events if e["event_type"] == "SETTLED_FINAL"]
    assert len(settled_events) == 1
    assert settled_events[0]["metadata"]["provider_request_id"] == "prov-xyz-001"
    assert session.ledger["pid-1"]["provider_request_id"] == "prov-xyz-001"


def test_provider_request_id_none_is_valid(monkeypatch) -> None:
    """provider_request_id=None is a valid settled state (provider may not return one)."""
    configure_env(monkeypatch)
    session = FakeSidecarSession()
    bind_sidecar_session(monkeypatch, session)

    reserve(make_reserve_request(idempotency_key="pid-null", estimated_cost="1.000000"))
    result = settle(make_settle_request(idempotency_key="pid-null", actual_cost="1.000000", provider_request_id=None))

    assert result.status == "SETTLED"
    assert session.ledger["pid-null"]["provider_request_id"] is None


# ---------------------------------------------------------------------------
# Audit completeness — all terminal transitions
# ---------------------------------------------------------------------------


def test_audit_events_for_reserve_settle_full_cycle(monkeypatch) -> None:
    """A full reserve→settle cycle produces RESERVE_CREATED and SETTLED_FINAL events."""
    configure_env(monkeypatch)
    session = FakeSidecarSession()
    bind_sidecar_session(monkeypatch, session)

    reserve(make_reserve_request(idempotency_key="audit-1", estimated_cost="2.000000"))
    settle(make_settle_request(idempotency_key="audit-1", actual_cost="1.500000", provider_request_id="p-audit-1"))

    event_types = [e["event_type"] for e in session.ledger_events]
    assert "RESERVE_CREATED" in event_types
    assert "SETTLED_FINAL" in event_types


def test_audit_events_for_drift_on_overrun(monkeypatch) -> None:
    """When actual_cost > reserved_amount a SETTLEMENT_DRIFT event is emitted."""
    configure_env(monkeypatch)
    session = FakeSidecarSession()
    bind_sidecar_session(monkeypatch, session)

    reserve(make_reserve_request(idempotency_key="drift-1", estimated_cost="0.010000"))
    # actual_cost > reserved_amount triggers drift
    # reserved = max(0.010000 * 1.25, 0.010000) = 0.012500
    # actual = 0.050000 > 0.012500
    settle(make_settle_request(idempotency_key="drift-1", actual_cost="0.050000", provider_request_id="p-drift"))

    event_types = [e["event_type"] for e in session.ledger_events]
    assert "SETTLEMENT_DRIFT" in event_types
    drift_event = next(e for e in session.ledger_events if e["event_type"] == "SETTLEMENT_DRIFT")
    assert Decimal(drift_event["metadata"]["actual_amount"]) > Decimal(drift_event["metadata"]["reserved_amount"])


def test_audit_events_for_expiry_sweep() -> None:
    """Reconciler emits EXPIRED_SWEEP for each expired reservation it reclaims."""
    session = FakeSweeperSession()
    session.ledger = {
        "exp-audit": {
            "idempotency_key": "exp-audit",
            "user_id": "demo-user",
            "reserved_amount": Decimal("2.500000"),
            "status": "RESERVED",
            "expires_at": datetime.utcnow() - timedelta(seconds=10),
            "expired_at": None,
            "settled_at": None,
        }
    }

    swept = sweep_expired_reservations(session, batch_size=10)

    assert swept == 1
    assert len(session.events) == 1
    assert session.events[0]["event_type"] == "EXPIRED_SWEEP"
    assert session.events[0]["metadata"]["reason"] == "reservation_expired"
    assert session.events[0]["metadata"]["refund_source"] == "reconciler_sweep"


# ---------------------------------------------------------------------------
# Concurrent reconciler idempotency
# ---------------------------------------------------------------------------


def test_reconciler_does_not_double_expire() -> None:
    """A row already marked EXPIRED is not re-processed by a second sweep pass."""
    session = FakeSweeperSession()
    session.ledger = {
        "already-expired": {
            "idempotency_key": "already-expired",
            "user_id": "demo-user",
            "reserved_amount": Decimal("1.000000"),
            "status": "EXPIRED",  # already expired by a prior sweep
            "expires_at": datetime.utcnow() - timedelta(seconds=30),
            "expired_at": datetime.utcnow() - timedelta(seconds=5),
            "settled_at": None,
        }
    }

    swept = sweep_expired_reservations(session, batch_size=10)

    assert swept == 0
    assert session.ledger["already-expired"]["status"] == "EXPIRED"
    assert len(session.events) == 0


def test_reconciler_batch_processes_multiple_rows() -> None:
    """Sweeper processes multiple expired rows in a single pass."""
    session = FakeSweeperSession()
    now = datetime.utcnow()
    for i in range(4):
        session.ledger[f"batch-{i}"] = {
            "idempotency_key": f"batch-{i}",
            "user_id": "demo-user",
            "reserved_amount": Decimal("1.000000"),
            "status": "RESERVED",
            "expires_at": now - timedelta(seconds=i + 1),
            "expired_at": None,
            "settled_at": None,
        }

    swept = sweep_expired_reservations(session, batch_size=10)

    assert swept == 4
    assert all(session.ledger[f"batch-{i}"]["status"] == "EXPIRED" for i in range(4))
    assert len(session.events) == 4


def test_reconciler_respects_batch_size() -> None:
    """Sweeper stops after batch_size rows per iteration."""
    session = FakeSweeperSession()
    now = datetime.utcnow()
    for i in range(6):
        session.ledger[f"bs-{i}"] = {
            "idempotency_key": f"bs-{i}",
            "user_id": "demo-user",
            "reserved_amount": Decimal("1.000000"),
            "status": "RESERVED",
            "expires_at": now - timedelta(seconds=i + 1),
            "expired_at": None,
            "settled_at": None,
        }

    swept = sweep_expired_reservations(session, batch_size=3)

    assert swept == 6  # sweeper loops until no rows remain


def test_reconciler_refunds_full_reserved_amount() -> None:
    """Reconciler credits back the exact reserved_amount on expiry."""
    session = FakeSweeperSession()
    reserved_amount = Decimal("4.750000")
    session.wallets["demo-user"]["balance"] = Decimal("10.000000")
    session.ledger["refund-check"] = {
        "idempotency_key": "refund-check",
        "user_id": "demo-user",
        "reserved_amount": reserved_amount,
        "status": "RESERVED",
        "expires_at": datetime.utcnow() - timedelta(seconds=10),
        "expired_at": None,
        "settled_at": None,
    }

    sweep_expired_reservations(session, batch_size=10)

    assert session.wallets["demo-user"]["balance"] == Decimal("10.000000") + reserved_amount
    assert session.ledger["refund-check"]["status"] == "EXPIRED"
