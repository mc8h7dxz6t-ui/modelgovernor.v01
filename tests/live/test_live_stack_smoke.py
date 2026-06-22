from __future__ import annotations

from decimal import Decimal
import json
import os
from urllib import request
import uuid

import psycopg


SIDECAR_URL = os.environ.get("LIVE_SIDECAR_URL", "http://localhost:8081")
SIDECAR_TOKEN = os.environ.get("LIVE_SIDECAR_TOKEN", "dev-sidecar-token")
DATABASE_URL = os.environ.get("LIVE_DATABASE_URL", "post******localhost:5432/modelgovernor")


def _post(path: str, payload: dict[str, object]) -> tuple[int, dict[str, object]]:
    req = request.Request(
        f"{SIDECAR_URL}{path}",
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={
            "Content-Type": "application/json",
            "X-Internal-Token": SIDECAR_TOKEN,
        },
    )
    with request.urlopen(req, timeout=10) as response:
        body = json.loads(response.read().decode("utf-8"))
        return response.status, body


def _get(path: str) -> tuple[int, dict[str, object]]:
    req = request.Request(
        f"{SIDECAR_URL}{path}",
        method="GET",
        headers={"X-Internal-Token": SIDECAR_TOKEN},
    )
    with request.urlopen(req, timeout=10) as response:
        body = json.loads(response.read().decode("utf-8"))
        return response.status, body


def _ensure_wallet(user_id: str, balance: Decimal) -> None:
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO user_wallets (user_id, balance, active)
                VALUES (%s, %s, TRUE)
                ON CONFLICT (user_id) DO UPDATE SET balance = EXCLUDED.balance, active = TRUE
                """,
                (user_id, balance),
            )
        conn.commit()


def test_live_reserve_then_settle_round_trip() -> None:
    user_id = "live-user"
    idem = f"live-{uuid.uuid4()}"
    _ensure_wallet(user_id=user_id, balance=Decimal("100.000000"))

    reserve_status, reserve_body = _post(
        "/reserve",
        {
            "user_id": user_id,
            "trace_id": "trace-live-1",
            "idempotency_key": idem,
            "model": "gpt-4o-mini",
            "estimated_cost": "1.500000",
        },
    )

    assert reserve_status == 200
    assert reserve_body["status"] == "RESERVED"

    settle_status, settle_body = _post(
        "/settle",
        {
            "idempotency_key": idem,
            "actual_cost": "1.200000",
            "provider_request_id": "provider-live-1",
        },
    )

    assert settle_status == 200
    assert settle_body["status"] == "SETTLED"

    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT status, actual_amount, provider_request_id FROM escrow_ledger WHERE idempotency_key = %s",
                (idem,),
            )
            row = cur.fetchone()

    assert row is not None
    assert row[0] == "SETTLED"
    assert str(row[1]) == "1.200000"
    assert row[2] == "provider-live-1"


def test_live_reconciliation_summary_endpoint_available() -> None:
    status_code, body = _get("/admin/reconciliation-summary")
    assert status_code == 200
    assert "matched_count" in body
    assert "mismatched_count" in body
    assert "resolved_count" in body
