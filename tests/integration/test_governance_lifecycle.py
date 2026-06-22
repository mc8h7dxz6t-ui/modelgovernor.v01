from contextlib import nullcontext
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
import sys
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from sidecar.app.policy import compute_reservation_amount
from sidecar.app.routes_reserve import reserve_funds
from sidecar.app.routes_settle import settle_funds
from sidecar.app.schemas import ReserveRequest, SettleRequest
from reconciler.app.sweeper import sweep_expired_reservations


class StatefulCursor:
    def __init__(self, state: dict):
        self.state = state
        self._rows: list[tuple] = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, query: str, params: tuple | None = None) -> None:
        params = params or ()
        q = " ".join(query.lower().split())

        if "select wallet_id, balance_available" in q:
            self._rows = [(self.state["wallet_id"], self.state["balance_available"]) ]
            return

        if "select policy_id, enabled, max_cost_per_request" in q:
            self._rows = [
                (
                    self.state["policy_id"],
                    self.state["policy_enabled"],
                    self.state["policy_max_cost_per_request"],
                )
            ]
            return

        if "select ledger_entry_id, reservation_status, amount_reserved, reserved_until" in q:
            ledger = self.state.get("ledger")
            if ledger:
                self._rows = [
                    (
                        ledger["ledger_entry_id"],
                        ledger["reservation_status"],
                        ledger["amount_reserved"],
                        ledger["reserved_until"],
                    )
                ]
            else:
                self._rows = []
            return

        if "update wallets set balance_available = balance_available -" in q:
            amount = params[0]
            self.state["balance_available"] -= amount
            self.state["balance_reserved"] += amount
            self._rows = []
            return

        if "insert into ledger_entries" in q:
            ledger_entry_id = uuid4()
            amount_reserved = params[4]
            reserved_until = params[5]
            self.state["ledger"] = {
                "ledger_entry_id": ledger_entry_id,
                "reservation_status": "RESERVED",
                "amount_reserved": amount_reserved,
                "amount_settled": Decimal("0"),
                "amount_released": Decimal("0"),
                "reserved_until": reserved_until,
            }
            self._rows = [(ledger_entry_id, "RESERVED", amount_reserved, reserved_until)]
            return

        if "insert into audit_events" in q:
            self.state.setdefault("audit_events", 0)
            self.state["audit_events"] += 1
            self._rows = []
            return

        if "select wallet_id from wallets" in q:
            self._rows = [(self.state["wallet_id"],)]
            return

        if "select ledger_entry_id, reservation_status, amount_reserved, amount_settled, amount_released" in q:
            ledger = self.state["ledger"]
            self._rows = [
                (
                    ledger["ledger_entry_id"],
                    ledger["reservation_status"],
                    ledger["amount_reserved"],
                    ledger["amount_settled"],
                    ledger["amount_released"],
                )
            ]
            return

        if "update ledger_entries set reservation_status = 'settled'" in q:
            settled_amount, released_amount = params[0], params[1]
            self.state["ledger"]["reservation_status"] = "SETTLED"
            self.state["ledger"]["amount_settled"] = settled_amount
            self.state["ledger"]["amount_released"] = released_amount
            self._rows = []
            return

        if "update wallets set balance_reserved = balance_reserved -" in q:
            amount_reserved, released_amount = params[0], params[1]
            self.state["balance_reserved"] -= amount_reserved
            self.state["balance_available"] += released_amount
            self._rows = []
            return

        raise AssertionError(f"Unexpected SQL executed: {query}")

    def fetchone(self):
        if not self._rows:
            return None
        return self._rows.pop(0)


class StatefulConnection:
    def __init__(self, state: dict):
        self.cursor_impl = StatefulCursor(state)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def transaction(self):
        return nullcontext()

    def cursor(self):
        return self.cursor_impl

    def close(self):
        return None


class SweepCursor:
    def __init__(self):
        self.query = ""
        self.params = ()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, query: str, params: tuple | None = None) -> None:
        self.query = " ".join(query.lower().split())
        self.params = params or ()

    def fetchone(self):
        return (2,)


class SweepConnection:
    def __init__(self):
        self.cursor_impl = SweepCursor()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def transaction(self):
        return nullcontext()

    def cursor(self):
        return self.cursor_impl

    def close(self):
        return None


def test_policy_reservation_is_bounded() -> None:
    assert compute_reservation_amount(Decimal("0")) == Decimal("0")
    assert compute_reservation_amount(Decimal("10")) == Decimal("11.000000")
    assert compute_reservation_amount(Decimal("1"), Decimal("9")) == Decimal("2.000000")


def test_reserve_settle_lifecycle_with_transactional_updates(monkeypatch) -> None:
    state = {
        "wallet_id": uuid4(),
        "policy_id": uuid4(),
        "policy_enabled": True,
        "policy_max_cost_per_request": Decimal("25.000000"),
        "balance_available": Decimal("100.000000"),
        "balance_reserved": Decimal("0"),
    }

    def fake_connection_factory():
        return StatefulConnection(state)

    monkeypatch.setattr("sidecar.app.routes_reserve.get_db_connection", fake_connection_factory)
    monkeypatch.setattr("sidecar.app.routes_settle.get_db_connection", fake_connection_factory)

    reserve_response = reserve_funds(
        ReserveRequest(
            tenant_id="default",
            wallet_ref="demo-user",
            provider="openai",
            model_name="gpt-4o-mini",
            idempotency_key="idem-1",
            request_id="req-1",
            estimated_cost=Decimal("10.000000"),
        )
    )

    assert reserve_response.reservation_status == "RESERVED"
    assert reserve_response.amount_reserved == Decimal("11.000000")
    assert state["balance_available"] == Decimal("89.000000")
    assert state["balance_reserved"] == Decimal("11.000000")
    assert datetime.fromisoformat(reserve_response.reserved_until) > datetime.now(UTC) - timedelta(seconds=5)

    settle_response = settle_funds(
        SettleRequest(
            tenant_id="default",
            wallet_ref="demo-user",
            idempotency_key="idem-1",
            realized_cost=Decimal("8.000000"),
            provider_request_id="provider-123",
        )
    )

    assert settle_response.reservation_status == "SETTLED"
    assert settle_response.amount_settled == Decimal("8.000000")
    assert settle_response.amount_released == Decimal("3.000000")
    assert state["ledger"]["reservation_status"] == "SETTLED"
    assert state["balance_available"] == Decimal("92.000000")
    assert state["balance_reserved"] == Decimal("0.000000")
    assert state["audit_events"] >= 2


def test_reconciler_sweeper_uses_skip_locked(monkeypatch) -> None:
    connection = SweepConnection()

    monkeypatch.setattr("reconciler.app.sweeper.get_db_connection", lambda: connection)

    swept = sweep_expired_reservations(batch_size=50)

    assert swept == 2
    assert "for update skip locked" in connection.cursor_impl.query
    assert connection.cursor_impl.params == (50,)
