"""ClaimGate production-depth load — FNOL ingest + Postgres idempotency under concurrency."""
from __future__ import annotations

import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from decimal import Decimal
from statistics import median

import pytest

from platforms.claim_gate.payment_rail import reset_payment_store, submit_payment
from platforms.common.integrations.fnol_adapter import normalize_fnol
from platforms.common.persistence.payment_store import get_payment_store, reset_payment_stores


def _fnol_payload(vendor: str, idx: int) -> dict:
    if vendor == "acturis":
        return {
            "notification": {
                "claimReference": f"ACT-LOAD-{idx}",
                "policyReference": "POL-MOTOR-UK-001",
                "dateOfLoss": "2025-05-01",
                "estimatedAmount": "3200.00",
                "currencyCode": "GBP",
                "notificationId": f"act-{idx}",
            }
        }
    return {
        "claim": {
            "claimNumber": f"GW-LOAD-{idx}",
            "policyNumber": "POL-AUTO-001",
            "lossDate": "2025-05-01",
            "reportedAmount": "5000.00",
            "id": f"gw-{idx}",
        }
    }


def _process_fnol_payment(vendor: str, idx: int) -> tuple[str, float]:
    start = time.perf_counter()
    fnol = normalize_fnol(vendor, _fnol_payload(vendor, idx))
    key = f"fnol-{fnol.vendor}-{fnol.raw_vendor_id}"
    first = submit_payment(
        claim_id=fnol.claim_id,
        amount=fnol.reported_amount,
        currency=fnol.currency,
        payee_id=fnol.claimant_id,
        idempotency_key=key,
        gate_decision="APPROVED",
        crystal_id=f"crystal-load-{idx}",
    )
    second = submit_payment(
        claim_id=fnol.claim_id,
        amount=fnol.reported_amount,
        currency=fnol.currency,
        payee_id=fnol.claimant_id,
        idempotency_key=key,
        gate_decision="APPROVED",
        crystal_id=f"crystal-load-{idx}",
    )
    status = "ok" if first.payment_id == second.payment_id else "idempotency_fail"
    return status, time.perf_counter() - start


@pytest.fixture(autouse=True)
def _reset_stores():
    reset_payment_stores()
    reset_payment_store()
    yield
    reset_payment_stores()
    reset_payment_store()


def test_fnol_idempotency_under_load():
    workers = int(os.environ.get("LOAD_WORKERS", "8"))
    ops = int(os.environ.get("LOAD_OPS_PER_WORKER", "5"))
    vendors = ["guidewire", "acturis"]

    latencies: list[float] = []
    failures = 0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [
            pool.submit(_process_fnol_payment, vendors[i % len(vendors)], i)
            for i in range(workers * ops)
        ]
        for fut in as_completed(futures):
            status, elapsed = fut.result()
            latencies.append(elapsed)
            if status != "ok":
                failures += 1

    assert failures == 0, f"idempotency failures: {failures}"
    assert median(latencies) < 1.0


def test_postgres_store_when_configured():
    if not os.environ.get("IG_PLATFORM_DATABASE_URL") and not os.environ.get("DATABASE_URL"):
        pytest.skip("postgres URL not configured")
    store = get_payment_store()
    from platforms.common.persistence.payment_types import PaymentInstruction, PaymentStatus

    instr = PaymentInstruction(
        payment_id="pay_pg_1",
        claim_id="pg-claim",
        idempotency_key="pg-idem-1",
        amount=Decimal("100"),
        currency="USD",
        payee_id="p1",
        status=PaymentStatus.COMPLETED,
        crystal_id="crystal-pg",
    )
    store.save(instr)
    again = store.get("pg-idem-1")
    assert again is not None
    assert again.payment_id == "pay_pg_1"
