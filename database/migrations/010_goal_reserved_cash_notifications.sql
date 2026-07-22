ALTER TABLE goals
ADD COLUMN IF NOT EXISTS archived BOOLEAN NOT NULL DEFAULT FALSE;

ALTER TABLE cash_buckets
ADD COLUMN IF NOT EXISTS goal_id INTEGER REFERENCES goals(id) ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS ix_cash_buckets_goal_id ON cash_buckets(goal_id);

CREATE UNIQUE INDEX IF NOT EXISTS uq_cash_buckets_goal_reserved
ON cash_buckets(goal_id)
WHERE goal_id IS NOT NULL AND bucket_type = 'goal_reserved';

CREATE TABLE IF NOT EXISTS goal_notifications (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    goal_id INTEGER NOT NULL REFERENCES goals(id) ON DELETE CASCADE,
    notification_type VARCHAR(50) NOT NULL,
    title VARCHAR(150) NOT NULL,
    message TEXT NOT NULL,
    read BOOLEAN NOT NULL DEFAULT FALSE,
    archived BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_goal_notification_type UNIQUE (goal_id, notification_type)
);

CREATE INDEX IF NOT EXISTS ix_goal_notifications_user_id ON goal_notifications(user_id);
CREATE INDEX IF NOT EXISTS ix_goal_notifications_goal_id ON goal_notifications(goal_id);
