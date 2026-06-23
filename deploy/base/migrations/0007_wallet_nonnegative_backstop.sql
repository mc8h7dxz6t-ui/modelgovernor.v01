-- Re-establish Postgres DB backstop for non-negative wallet balances.
-- Application probes remain authoritative for detection; this constraint
-- prevents silent corruption if a bug bypasses runtime checks.

ALTER TABLE user_wallets
ADD CONSTRAINT user_wallets_nonnegative_balance CHECK (balance >= 0);
