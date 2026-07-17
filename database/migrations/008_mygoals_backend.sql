ALTER TABLE goals ADD COLUMN IF NOT EXISTS status VARCHAR(20) NOT NULL DEFAULT 'on_track';
ALTER TABLE goals ADD COLUMN IF NOT EXISTS category_details JSONB NOT NULL DEFAULT '{}'::jsonb;

CREATE TABLE IF NOT EXISTS goal_progress (
    id SERIAL PRIMARY KEY,
    goal_id INTEGER NOT NULL REFERENCES goals(id) ON DELETE CASCADE,
    amount NUMERIC(14, 2) NOT NULL CHECK (amount > 0),
    progress_date DATE NOT NULL,
    note TEXT,
    source VARCHAR(50) NOT NULL DEFAULT 'manual',
    new_current_amount NUMERIC(14, 2) NOT NULL CHECK (new_current_amount >= 0),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS goal_allocation_settings (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    cash_allocatable_ratio NUMERIC(5, 2) NOT NULL DEFAULT 50 CHECK (cash_allocatable_ratio BETWEEN 0 AND 100),
    monthly_allocatable_ratio NUMERIC(5, 2) NOT NULL DEFAULT 50 CHECK (monthly_allocatable_ratio BETWEEN 0 AND 100),
    goal_monthly_ratios JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS cash_buckets (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    bucket_type VARCHAR(30) NOT NULL,
    name VARCHAR(100),
    amount NUMERIC(14, 2) NOT NULL DEFAULT 0 CHECK (amount >= 0),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_goal_progress_goal_id ON goal_progress(goal_id);
CREATE INDEX IF NOT EXISTS ix_goal_allocation_settings_user_id ON goal_allocation_settings(user_id);
CREATE INDEX IF NOT EXISTS ix_cash_buckets_user_id ON cash_buckets(user_id);
