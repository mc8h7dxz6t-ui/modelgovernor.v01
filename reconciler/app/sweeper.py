from .db import get_db_connection


def sweep_expired_reservations(batch_size: int = 100) -> int:
    """Sweep stale RESERVED ledger entries with row locking."""
    with get_db_connection() as conn:
        with conn.transaction():
            with conn.cursor() as cur:
                cur.execute(
                    """
                    WITH expired AS (
                        SELECT ledger_entry_id, wallet_id, amount_reserved
                        FROM ledger_entries
                        WHERE reservation_status = 'RESERVED'
                          AND reserved_until < NOW()
                        ORDER BY reserved_until ASC
                        FOR UPDATE SKIP LOCKED
                        LIMIT %s
                    ),
                    wallet_updates AS (
                        UPDATE wallets w
                        SET balance_available = w.balance_available + e.amount_reserved,
                            balance_reserved = w.balance_reserved - e.amount_reserved,
                            updated_at = NOW()
                        FROM expired e
                        WHERE w.wallet_id = e.wallet_id
                        RETURNING e.ledger_entry_id, e.wallet_id, e.amount_reserved
                    ),
                    ledger_updates AS (
                        UPDATE ledger_entries l
                        SET reservation_status = 'EXPIRED',
                            amount_released = wu.amount_reserved,
                            updated_at = NOW()
                        FROM wallet_updates wu
                        WHERE l.ledger_entry_id = wu.ledger_entry_id
                        RETURNING l.ledger_entry_id, wu.wallet_id, wu.amount_reserved
                    ),
                    audit_inserts AS (
                        INSERT INTO audit_events (
                            ledger_entry_id,
                            wallet_id,
                            event_type,
                            actor_type,
                            actor_id,
                            event_payload
                        )
                        SELECT
                            lu.ledger_entry_id,
                            lu.wallet_id,
                            'EXPIRED_SWEEP',
                            'service',
                            'reconciler',
                            jsonb_build_object('amount_released', lu.amount_reserved)
                        FROM ledger_updates lu
                        RETURNING audit_event_id
                    )
                    SELECT COUNT(*) FROM ledger_updates
                    """,
                    (batch_size,),
                )
                row = cur.fetchone()
                return int(row[0]) if row else 0
