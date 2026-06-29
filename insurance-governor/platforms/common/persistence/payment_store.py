"""Payment idempotency store — Postgres (HA) with in-memory fallback."""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from .db import platform_connection, platform_db_enabled
from .payment_types import PaymentInstruction, PaymentStatus


class MemoryPaymentStore:
    def __init__(self) -> None:
        self._data: dict[str, PaymentInstruction] = {}

    def get(self, idempotency_key: str) -> PaymentInstruction | None:
        return self._data.get(idempotency_key)

    def save(self, instruction: PaymentInstruction) -> PaymentInstruction:
        self._data[instruction.idempotency_key] = instruction
        return instruction

    def clear(self) -> None:
        self._data.clear()


class PostgresPaymentStore:
    def get(self, idempotency_key: str) -> PaymentInstruction | None:
        with platform_connection() as conn:
            if conn is None:
                return None
            row = conn.execute(
                """
                SELECT payment_id, claim_id, amount, currency, payee_id, status, rail,
                       reference, crystal_id, external_ref, idempotency_key
                FROM payment_idempotency WHERE idempotency_key = %s
                """,
                (idempotency_key,),
            ).fetchone()
            if row is None:
                return None
            return PaymentInstruction(
                payment_id=row[0],
                claim_id=row[1],
                amount=Decimal(str(row[2])),
                currency=row[3],
                payee_id=row[4],
                status=PaymentStatus(row[5]),
                rail=row[6],
                reference=row[7],
                crystal_id=row[8],
                external_ref=row[9],
                idempotency_key=row[10],
            )

    def save(self, instruction: PaymentInstruction) -> PaymentInstruction:
        with platform_connection() as conn:
            if conn is None:
                raise RuntimeError("postgres payment store unavailable")
            conn.execute(
                """
                INSERT INTO payment_idempotency (
                    idempotency_key, payment_id, claim_id, amount, currency, payee_id,
                    status, rail, reference, crystal_id, external_ref, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (idempotency_key) DO UPDATE SET
                    status = EXCLUDED.status,
                    reference = EXCLUDED.reference,
                    crystal_id = EXCLUDED.crystal_id,
                    external_ref = EXCLUDED.external_ref,
                    updated_at = EXCLUDED.updated_at
                """,
                (
                    instruction.idempotency_key,
                    instruction.payment_id,
                    instruction.claim_id,
                    instruction.amount,
                    instruction.currency,
                    instruction.payee_id,
                    instruction.status.value,
                    instruction.rail,
                    instruction.reference,
                    instruction.crystal_id,
                    instruction.external_ref,
                    datetime.now(timezone.utc),
                ),
            )
            conn.commit()
        return instruction

    def clear(self) -> None:
        with platform_connection() as conn:
            if conn is None:
                return
            conn.execute("DELETE FROM payment_idempotency")
            conn.commit()


_STORE: MemoryPaymentStore | PostgresPaymentStore | None = None


def get_payment_store() -> MemoryPaymentStore | PostgresPaymentStore:
    global _STORE
    if _STORE is None:
        _STORE = PostgresPaymentStore() if platform_db_enabled() else MemoryPaymentStore()
    return _STORE


def reset_payment_stores() -> None:
    global _STORE
    _STORE = None
