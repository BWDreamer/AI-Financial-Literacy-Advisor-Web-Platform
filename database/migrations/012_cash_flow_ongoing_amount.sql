ALTER TABLE cash_flows
    ADD COLUMN IF NOT EXISTS ongoing_amount NUMERIC(14, 2)
    NOT NULL DEFAULT 0;

ALTER TABLE cash_flows
    DROP CONSTRAINT IF EXISTS ck_cash_flows_ongoing_amount;

ALTER TABLE cash_flows
    ADD CONSTRAINT ck_cash_flows_ongoing_amount
    CHECK (ongoing_amount >= 0 AND ongoing_amount <= amount);
