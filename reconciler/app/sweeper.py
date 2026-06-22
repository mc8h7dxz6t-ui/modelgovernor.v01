from sqlalchemy import text
from sqlalchemy.orm import Session


def sweep_expired_reservations(session: Session, batch_size: int = 100) -> int:
    query = text(
        """
        SELECT idempotency_key
        FROM escrow_ledger
        WHERE status = 'RESERVED'
          AND expires_at <= CURRENT_TIMESTAMP
        ORDER BY expires_at ASC
        LIMIT :batch_size
        """
    )
    rows = session.execute(query, {"batch_size": batch_size}).fetchall()
    return len(rows)
