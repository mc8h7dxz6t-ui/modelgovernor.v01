"""H1 — Postgres transaction advisory lock for hash-chain append serialization."""

from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


@contextmanager
def chain_append_lock(session: Session, *, lock_key: int) -> Iterator[None]:
    """Serialize cross-process append paths on a single governor chain.

    Uses ``pg_advisory_xact_lock`` so the lock is held for the surrounding
    transaction and released automatically on commit or rollback.  On SQLite
    (local tests) this is a no-op pass-through.
    """
    if session.bind.dialect.name != "postgresql":
        yield
        return

    session.execute(
        text("SELECT pg_advisory_xact_lock(:lock_key)"),
        {"lock_key": lock_key},
    )
    logger.debug("chain append advisory xact lock acquired key=0x%x", lock_key)
    try:
        yield
    finally:
        logger.debug("chain append advisory xact lock released key=0x%x", lock_key)
