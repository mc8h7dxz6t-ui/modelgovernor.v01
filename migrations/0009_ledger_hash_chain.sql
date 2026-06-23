-- Tamper-evident hash chain columns for ledger_events (enterprise audit trail).

ALTER TABLE ledger_events
    ADD COLUMN IF NOT EXISTS prev_hash CHAR(64),
    ADD COLUMN IF NOT EXISTS row_hash CHAR(64);

CREATE INDEX IF NOT EXISTS idx_ledger_events_row_hash
    ON ledger_events (row_hash)
    WHERE row_hash IS NOT NULL;
