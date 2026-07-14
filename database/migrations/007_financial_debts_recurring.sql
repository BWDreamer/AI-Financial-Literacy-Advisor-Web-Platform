CREATE TABLE IF NOT EXISTS debts (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    debt_type VARCHAR(30) NOT NULL,
    name VARCHAR(100) NOT NULL,
    balance NUMERIC(14, 2) NOT NULL CHECK (balance >= 0),
    minimum_payment NUMERIC(14, 2) CHECK (minimum_payment >= 0),
    interest_rate NUMERIC(7, 4) CHECK (interest_rate >= 0 AND interest_rate <= 100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS recurring_cash_flows (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    flow_type VARCHAR(20) NOT NULL,
    name VARCHAR(100) NOT NULL,
    amount NUMERIC(14, 2) NOT NULL CHECK (amount >= 0),
    frequency VARCHAR(20) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE,
    category VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CHECK (end_date IS NULL OR end_date >= start_date)
);

CREATE INDEX IF NOT EXISTS ix_debts_user_id ON debts(user_id);
CREATE INDEX IF NOT EXISTS ix_recurring_cash_flows_user_id ON recurring_cash_flows(user_id);
