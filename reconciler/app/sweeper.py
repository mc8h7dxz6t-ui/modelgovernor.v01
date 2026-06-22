from sqlalchemy import text
from sqlalchemy.orm import Session


def sweep_expired_reservations(session: Session, batch_size: int = 100) -> int:
    total_swept = 0

    while True:
        with session.begin():
            rows = session.execute(
                text(
                    """
                    SELECT idempotency_key, user_id, reserved_amount
                    FROM escrow_ledger
                    WHERE status = 'RESERVED'
                      AND settled_at IS NULL
                      AND expired_at IS NULL
                      AND expires_at <= CURRENT_TIMESTAMP
                    ORDER BY expires_at ASC, idempotency_key ASC
                    FOR UPDATE SKIP LOCKED
                    LIMIT :batch_size
                    """
                ),
                {"batch_size": batch_size},
            ).mappings().all()

            if not rows:
                return total_swept

            for row in rows:
                wallet_row = session.execute(
                    text(
                        """
                        SELECT user_id
                        FROM user_wallets
                        WHERE user_id = :user_id
                        FOR UPDATE
                        """
                    ),
                    {"user_id": row["user_id"]},
                ).mappings().first()

                if wallet_row is None:
                    raise RuntimeError(f"wallet not found for user_id={row['user_id']}")

                expired_row = session.execute(
                    text(
                        """
                        UPDATE escrow_ledger
                        SET status = 'EXPIRED',
                            terminal_reason = 'expired_by_reconciler',
                            expired_at = COALESCE(expired_at, CURRENT_TIMESTAMP),
                            updated_at = CURRENT_TIMESTAMP
                        WHERE idempotency_key = :idempotency_key
                          AND status = 'RESERVED'
                          AND settled_at IS NULL
                          AND expired_at IS NULL
                        RETURNING idempotency_key
                        """
                    ),
                    {"idempotency_key": row["idempotency_key"]},
                ).first()

                if expired_row is None:
                    continue

                session.execute(
                    text(
                        """
                        UPDATE user_wallets
                        SET balance = balance + :refund_amount,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE user_id = :user_id
                        """
                    ),
                    {"refund_amount": row["reserved_amount"], "user_id": row["user_id"]},
                )

                session.execute(
                    text(
                        """
                        INSERT INTO ledger_events (
                            idempotency_key,
                            user_id,
                            event_type,
                            amount_delta,
                            metadata
                        )
                        VALUES (
                            :idempotency_key,
                            :user_id,
                            'EXPIRED_SWEEP',
                            :amount_delta,
                            CAST(:metadata AS JSONB)
                        )
                        """
                    ),
                    {
                        "idempotency_key": row["idempotency_key"],
                        "user_id": row["user_id"],
                        "amount_delta": row["reserved_amount"],
                        "metadata": '{"reason": "reservation_expired", "refund_source": "reconciler_sweep"}',
                    },
                )

                total_swept += 1
