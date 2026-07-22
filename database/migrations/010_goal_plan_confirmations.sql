CREATE TABLE IF NOT EXISTS goal_plan_confirmations (
    id SERIAL PRIMARY KEY,
    conversation_id INTEGER NOT NULL REFERENCES ai_conversations(id) ON DELETE CASCADE,
    plan_fingerprint VARCHAR(64) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_goal_plan_confirmations_conversation_plan
        UNIQUE (conversation_id, plan_fingerprint)
);

CREATE INDEX IF NOT EXISTS ix_goal_plan_confirmations_conversation_id
    ON goal_plan_confirmations(conversation_id);
