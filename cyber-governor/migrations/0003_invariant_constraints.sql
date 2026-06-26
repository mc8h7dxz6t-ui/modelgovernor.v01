-- Institutional++ DB invariant backstops (zero error budget at storage layer).

ALTER TABLE principal_budgets
    DROP CONSTRAINT IF EXISTS fg_account_nonnegative,
    ADD CONSTRAINT cg_principal_nonnegative CHECK (balance >= 0);

ALTER TABLE action_budget_state
    DROP CONSTRAINT IF EXISTS fg_exposure_cap_nonnegative,
    DROP CONSTRAINT IF EXISTS fg_exposure_reserved_within_cap,
    ADD CONSTRAINT cg_action_cap_nonnegative CHECK (cap_amount >= 0),
    ADD CONSTRAINT cg_action_reserved_within_cap CHECK (reserved_total <= cap_amount);

ALTER TABLE action_escrow_ledger
    DROP CONSTRAINT IF EXISTS fg_escrow_nonnegative_reserved,
    DROP CONSTRAINT IF EXISTS fg_escrow_nonnegative_committed,
    DROP CONSTRAINT IF EXISTS cg_escrow_nonnegative_reserved,
    DROP CONSTRAINT IF EXISTS cg_escrow_nonnegative_committed,
    ADD CONSTRAINT cg_escrow_nonnegative_reserved CHECK (reserved_exposure >= 0),
    ADD CONSTRAINT cg_escrow_nonnegative_committed CHECK (committed_exposure >= 0);
