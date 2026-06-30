CREATE TABLE IF NOT EXISTS assets (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    asset_type VARCHAR(20) NOT NULL,
    name VARCHAR(100) NOT NULL,
    amount NUMERIC(14, 2) NOT NULL CHECK (amount >= 0),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS cash_flows (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    flow_type VARCHAR(20) NOT NULL,
    name VARCHAR(100) NOT NULL,
    amount NUMERIC(14, 2) NOT NULL CHECK (amount >= 0),
    date DATE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE ai_conversations
    DROP CONSTRAINT IF EXISTS ai_conversations_user_id_key;
ALTER TABLE ai_conversations
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
UPDATE ai_conversations SET title = 'New Conversation' WHERE title IS NULL;
ALTER TABLE ai_conversations ALTER COLUMN title SET DEFAULT 'New Conversation';
ALTER TABLE ai_conversations ALTER COLUMN title SET NOT NULL;

CREATE INDEX IF NOT EXISTS ix_assets_user_id ON assets(user_id);
CREATE INDEX IF NOT EXISTS ix_cash_flows_user_id ON cash_flows(user_id);
CREATE INDEX IF NOT EXISTS ix_ai_conversations_user_id ON ai_conversations(user_id);
CREATE INDEX IF NOT EXISTS ix_ai_messages_conversation_id ON ai_messages(conversation_id);
