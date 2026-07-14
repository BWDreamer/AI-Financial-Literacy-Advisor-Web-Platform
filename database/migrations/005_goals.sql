CREATE TABLE IF NOT EXISTS goals (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    category VARCHAR(50) NOT NULL,
    target_amount NUMERIC(14, 2) NOT NULL CHECK (target_amount > 0),
    current_amount NUMERIC(14, 2) NOT NULL DEFAULT 0 CHECK (current_amount >= 0 AND current_amount <= target_amount),
    monthly_contribution NUMERIC(14, 2) NOT NULL DEFAULT 0 CHECK (monthly_contribution >= 0),
    target_date DATE NOT NULL,
    priority INTEGER NOT NULL DEFAULT 1 CHECK (priority BETWEEN 1 AND 5),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS goal_contributions (
    id SERIAL PRIMARY KEY,
    goal_id INTEGER NOT NULL REFERENCES goals(id) ON DELETE CASCADE,
    amount NUMERIC(14, 2) NOT NULL CHECK (amount > 0),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_goals_user_id ON goals(user_id);
CREATE INDEX IF NOT EXISTS ix_goal_contributions_goal_id ON goal_contributions(goal_id);
