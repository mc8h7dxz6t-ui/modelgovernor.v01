ALTER TABLE user_wallets
ADD CONSTRAINT user_wallets_nonnegative_balance CHECK (balance >= 0);

CREATE INDEX idx_escrow_request_fingerprint
ON escrow_ledger (request_fingerprint);

CREATE UNIQUE INDEX idx_escrow_provider_request_id_unique
ON escrow_ledger (provider_request_id)
WHERE provider_request_id IS NOT NULL;

ALTER TABLE escrow_ledger
ADD CONSTRAINT escrow_status_timestamp_consistency CHECK (
    (status = 'RESERVED' AND settled_at IS NULL AND expired_at IS NULL)
    OR
    (status = 'SETTLED' AND settled_at IS NOT NULL AND expired_at IS NULL)
    OR
    (status = 'EXPIRED' AND expired_at IS NOT NULL AND settled_at IS NULL)
    OR
    (status = 'REFUNDED')
);

ALTER TABLE ledger_events
ADD CONSTRAINT ledger_events_idempotency_key_fkey
FOREIGN KEY (idempotency_key) REFERENCES escrow_ledger(idempotency_key);

ALTER TABLE ledger_events
ADD CONSTRAINT ledger_events_user_id_fkey
FOREIGN KEY (user_id) REFERENCES user_wallets(user_id);
