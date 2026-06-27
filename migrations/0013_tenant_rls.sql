-- Postgres Row-Level Security (RLS) for multi-tenant isolation (institutional++).
-- Apply on PostgreSQL only. SQLite unit tests skip this migration.
--
-- Gold standard: engine-enforced tenant boundary — not application WHERE clauses alone.

-- Propagate tenant_id onto ledger_events for RLS (denormalized from escrow at write time).
ALTER TABLE ledger_events
    ADD COLUMN IF NOT EXISTS tenant_id VARCHAR(255) NOT NULL DEFAULT 'default-tenant';

CREATE INDEX IF NOT EXISTS idx_ledger_events_tenant_recorded
    ON ledger_events (tenant_id, recorded_at DESC);

-- Safe tenant resolver: invalid / missing session var → NULL (policy denies rows).
CREATE OR REPLACE FUNCTION app_current_tenant_id() RETURNS text
    LANGUAGE sql
    STABLE
AS $$
    SELECT NULLIF(trim(current_setting('app.current_tenant_id', true)), '')
$$;

-- Application runtime role (created by ops; migration grants if role exists).
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'governor_app') THEN
        CREATE ROLE governor_app NOLOGIN;
    END IF;
END
$$;

-- escrow_ledger
ALTER TABLE escrow_ledger ENABLE ROW LEVEL SECURITY;
ALTER TABLE escrow_ledger FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tenant_isolation_escrow ON escrow_ledger;
CREATE POLICY tenant_isolation_escrow ON escrow_ledger
    FOR ALL
    TO governor_app
    USING (
        app_current_tenant_id() IS NOT NULL
        AND tenant_id = app_current_tenant_id()
    )
    WITH CHECK (
        app_current_tenant_id() IS NOT NULL
        AND tenant_id = app_current_tenant_id()
    );

-- ledger_events
ALTER TABLE ledger_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE ledger_events FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tenant_isolation_ledger_events ON ledger_events;
CREATE POLICY tenant_isolation_ledger_events ON ledger_events
    FOR ALL
    TO governor_app
    USING (
        app_current_tenant_id() IS NOT NULL
        AND tenant_id = app_current_tenant_id()
    )
    WITH CHECK (
        app_current_tenant_id() IS NOT NULL
        AND tenant_id = app_current_tenant_id()
    );

-- guardrail_incidents
ALTER TABLE guardrail_incidents ENABLE ROW LEVEL SECURITY;
ALTER TABLE guardrail_incidents FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tenant_isolation_guardrail ON guardrail_incidents;
CREATE POLICY tenant_isolation_guardrail ON guardrail_incidents
    FOR ALL
    TO governor_app
    USING (
        app_current_tenant_id() IS NOT NULL
        AND tenant_id = app_current_tenant_id()
    )
    WITH CHECK (
        app_current_tenant_id() IS NOT NULL
        AND tenant_id = app_current_tenant_id()
    );

GRANT SELECT, INSERT, UPDATE ON escrow_ledger TO governor_app;
GRANT SELECT, INSERT, UPDATE ON ledger_events TO governor_app;
GRANT SELECT, INSERT, UPDATE ON guardrail_incidents TO governor_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO governor_app;
