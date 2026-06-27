"""Postgres Row-Level Security session binding — institutional++ tenant isolation.

Gold standard:
- Validate tenant_id before SET LOCAL (no invalid cast in RLS).
- SET LOCAL inside transaction scope.
- RESET ALL before connection returns to pool (prevents ghost-tenant leak).
- Pool checkout hook resets session state (defense in depth).
"""
from __future__ import annotations

import logging
import re
from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import Pool

logger = logging.getLogger(__name__)

_TENANT_ID_PATTERN = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._:-]{0,127}$")


class TenantValidationError(ValueError):
    pass


def validate_tenant_id(tenant_id: str) -> str:
    normalized = tenant_id.strip()
    if not normalized or not _TENANT_ID_PATTERN.fullmatch(normalized):
        raise TenantValidationError(f"invalid tenant_id format: {tenant_id!r}")
    return normalized


def bind_tenant_session(session: Session, tenant_id: str) -> str:
    """Bind tenant context for RLS within the current transaction."""
    safe_tenant = validate_tenant_id(tenant_id)
    dialect = session.bind.dialect.name if session.bind else "sqlite"
    if dialect == "sqlite":
        return safe_tenant
    session.execute(
        text("SELECT set_config('app.current_tenant_id', :tenant, true)"),
        {"tenant": safe_tenant},
    )
    return safe_tenant


def reset_session_context(session: Session) -> None:
    """Clear transaction-local and session state before pool return."""
    if session.bind is None:
        return
    dialect = session.bind.dialect.name
    if dialect == "sqlite":
        return
    try:
        session.execute(text("RESET ALL"))
    except Exception:
        logger.exception("failed to RESET ALL on session teardown")


@contextmanager
def tenant_scoped_session(session: Session, tenant_id: str) -> Iterator[Session]:
    """Yield session with RLS tenant bound; always reset on exit."""
    bind_tenant_session(session, tenant_id)
    try:
        yield session
    finally:
        reset_session_context(session)


def install_pool_tenant_reset(engine: Engine) -> None:
    """On pool checkout, wipe session variables (ghost-tenant leak prevention)."""

    @event.listens_for(engine, "connect")
    def _on_connect(dbapi_connection, connection_record) -> None:  # noqa: ANN001
        if engine.dialect.name == "sqlite":
            return
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute("RESET ALL")
        except Exception:
            logger.debug("RESET ALL on connect skipped", exc_info=True)
        finally:
            cursor.close()

    @event.listens_for(Pool, "checkout")
    def _on_checkout(dbapi_connection, connection_record, connection_proxy) -> None:  # noqa: ANN001
        if engine.dialect.name == "sqlite":
            return
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute("RESET ALL")
        except Exception:
            logger.debug("RESET ALL on checkout skipped", exc_info=True)
        finally:
            cursor.close()


def extract_tenant_from_claims(claims: dict, *, claim_name: str = "tenant_id") -> str | None:
    for key in (claim_name, "tenant_id", "https://governor.io/tenant_id"):
        value = claims.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return None
