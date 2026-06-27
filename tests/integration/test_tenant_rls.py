"""Tests for tenant RLS session binding."""
from __future__ import annotations

import pytest

from sidecar.app.tenant_rls import (
    TenantValidationError,
    bind_tenant_session,
    extract_tenant_from_claims,
    reset_session_context,
    validate_tenant_id,
)


def test_validate_tenant_id_accepts_safe_values() -> None:
    assert validate_tenant_id("acme-corp") == "acme-corp"
    assert validate_tenant_id("tenant_01") == "tenant_01"


def test_validate_tenant_id_rejects_injection() -> None:
    with pytest.raises(TenantValidationError):
        validate_tenant_id("'; DROP TABLE escrow_ledger; --")
    with pytest.raises(TenantValidationError):
        validate_tenant_id("")


def test_extract_tenant_from_claims_prefers_configured_claim() -> None:
    claims = {"tenant_id": "t1", "https://governor.io/tenant_id": "t2"}
    assert extract_tenant_from_claims(claims, claim_name="tenant_id") == "t1"


def test_bind_and_reset_sqlite_noop(tmp_path, monkeypatch) -> None:
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import Session

    engine = create_engine(f"sqlite:///{tmp_path}/t.sqlite3")
    monkeypatch.setenv("DATABASE_URL", str(engine.url))
    with Session(engine) as session:
        bind_tenant_session(session, "tenant-a")
        reset_session_context(session)
        row = session.execute(text("SELECT 1")).scalar()
        assert row == 1
