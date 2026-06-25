from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

RECONCILER_LEADER_LOCK_KEY = 0x46475F524543  # FG_REC


@contextmanager
def reconciler_leader_session(session: Session, *, lock_key: int = RECONCILER_LEADER_LOCK_KEY) -> Iterator[bool]:
    if session.bind.dialect.name != "postgresql":
        yield True
        return
    acquired = session.execute(text("SELECT pg_try_advisory_lock(:k)"), {"k": lock_key}).scalar_one()
    if not acquired:
        logger.info("fg reconciler standby")
        yield False
        return
    try:
        yield True
    finally:
        session.execute(text("SELECT pg_advisory_unlock(:k)"), {"k": lock_key})
