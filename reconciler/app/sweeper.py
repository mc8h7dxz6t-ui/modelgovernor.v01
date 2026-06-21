from datetime import UTC, datetime

from .db import get_db_connection


def sweep_expired_reservations(batch_size: int = 100) -> int:
    """Sweep stale RESERVED ledger entries.

    TODO: replace placeholder with a transactional workflow equivalent to:
    - SELECT ledger_entry_id, wallet_id, amount_reserved
      FROM ledger_entries
      WHERE reservation_status = 'RESERVED' AND reserved_until < NOW()
      FOR UPDATE SKIP LOCKED
      LIMIT %(batch_size)s
    - increment wallet balance_available and decrement balance_reserved
    - update ledger_entries reservation_status='EXPIRED', amount_released=amount_reserved
    - insert audit_events with event_type='EXPIRED_SWEEP'
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT %s", (datetime.now(UTC).isoformat(),))
            _ = cur.fetchone()
    return 0
