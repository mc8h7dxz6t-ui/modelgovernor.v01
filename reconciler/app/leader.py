"""Postgres advisory-lock leader election for reconciler HA."""
from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Stable 64-bit advisory lock key for finance-ops reconciler leadership.
RECONCILER_LEADER_LOCK_KEY = 0x4D474F565F524543  # "MGOV_REC" as hex int


@contextmanager
def reconciler_leader_session(session: Session, *, lock_key: int = RECONCILER_LEADER_LOCK_KEY) -> Iterator[bool]:
    """Attempt to acquire reconciler leadership for the duration of the context.

    Uses ``pg_try_advisory_lock`` on Postgres.  On SQLite (tests), leadership is
    always granted so local harnesses remain simple.
    """
    if session.bind.dialect.name != "postgresql":
        yield True
        return

    acquired = session.execute(
        text("SELECT pg_try_advisory_lock(:lock_key)"),
        {"lock_key": lock_key},
    ).scalar_one()
    if not acquired:
        logger.info("reconciler leadership not acquired; standing by")
        yield False
        return

    try:
        yield True
    finally:
        session.execute(text("SELECT pg_advisory_unlock(:lock_key)"), {"lock_key": lock_key})
