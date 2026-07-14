CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(50),
    first_name VARCHAR(50),
    last_name VARCHAR(50),
    avatar_url TEXT,
    password_hash TEXT NOT NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'user',
    last_seen_at TIMESTAMPTZ,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE users ADD COLUMN IF NOT EXISTS first_name VARCHAR(50);
ALTER TABLE users ADD COLUMN IF NOT EXISTS last_name VARCHAR(50);
ALTER TABLE users ADD COLUMN IF NOT EXISTS last_seen_at TIMESTAMPTZ;

CREATE TABLE IF NOT EXISTS user_profiles (
    id SERIAL PRIMARY KEY,
    user_id INTEGER UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    region VARCHAR(100),
    monthly_income NUMERIC(12, 2),
    fixed_expenses NUMERIC(12, 2),
    current_savings NUMERIC(12, 2),
    initial_savings_target NUMERIC(12, 2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS financial_rules (
    id SERIAL PRIMARY KEY,
    region VARCHAR(100) NOT NULL,
    category VARCHAR(100) NOT NULL,
    rule_year VARCHAR(20) NOT NULL,
    rule_key VARCHAR(100) NOT NULL,
    rule_value TEXT NOT NULL,
    source_name VARCHAR(255),
    source_url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ai_conversations (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL DEFAULT 'New Conversation',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ai_messages (
    id SERIAL PRIMARY KEY,
    conversation_id INTEGER REFERENCES ai_conversations(id) ON DELETE CASCADE,
    sender VARCHAR(50) NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

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

CREATE TABLE IF NOT EXISTS user_memories (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    category VARCHAR(50) NOT NULL DEFAULT 'other',
    fact TEXT NOT NULL,
    source VARCHAR(50) NOT NULL DEFAULT 'manual',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_used_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_assets_user_id ON assets(user_id);
CREATE INDEX IF NOT EXISTS ix_cash_flows_user_id ON cash_flows(user_id);
CREATE INDEX IF NOT EXISTS ix_ai_conversations_user_id ON ai_conversations(user_id);
CREATE INDEX IF NOT EXISTS ix_ai_messages_conversation_id ON ai_messages(conversation_id);
CREATE INDEX IF NOT EXISTS ix_user_memories_user_id ON user_memories(user_id);

CREATE TABLE IF NOT EXISTS articles (
    id VARCHAR(100) PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    summary TEXT NOT NULL,
    cover_image_url TEXT,
    author_name VARCHAR(100) NOT NULL,
    source_name VARCHAR(100) NOT NULL,
    category VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'draft',
    published_at TIMESTAMPTZ,
    views INTEGER NOT NULL DEFAULT 0,
    likes INTEGER NOT NULL DEFAULT 0,
    saves INTEGER NOT NULL DEFAULT 0,
    content_blocks JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS article_likes (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    article_id VARCHAR(100) NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_article_likes_user_article UNIQUE (user_id, article_id)
);

CREATE TABLE IF NOT EXISTS article_saves (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    article_id VARCHAR(100) NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_article_saves_user_article UNIQUE (user_id, article_id)
);

CREATE INDEX IF NOT EXISTS ix_articles_category ON articles(category);
CREATE INDEX IF NOT EXISTS ix_articles_status ON articles(status);
CREATE INDEX IF NOT EXISTS ix_articles_published_at ON articles(published_at);
CREATE INDEX IF NOT EXISTS ix_article_likes_user_id ON article_likes(user_id);
CREATE INDEX IF NOT EXISTS ix_article_likes_article_id ON article_likes(article_id);
CREATE INDEX IF NOT EXISTS ix_article_saves_user_id ON article_saves(user_id);
CREATE INDEX IF NOT EXISTS ix_article_saves_article_id ON article_saves(article_id);

INSERT INTO articles (
    id,
    title,
    summary,
    cover_image_url,
    author_name,
    source_name,
    category,
    status,
    published_at,
    views,
    likes,
    saves,
    content_blocks
) VALUES
(
    'budget-start',
    'How to Build a Budget That Survives Real Life',
    'A simple guide to tracking income, planning spending and leaving room for irregular costs.',
    'https://images.unsplash.com/photo-1554224155-6726b3ff858f?auto=format&fit=crop&w=900&q=80',
    'FinanceAI Learning Team',
    'Knowledge Base',
    'Budgeting',
    'published',
    '2026-07-02T09:30:00+10:00',
    1820,
    126,
    48,
    '[{"type":"paragraph","text":"A useful budget starts with the money that actually arrives in your account and the spending that actually leaves it."},{"type":"paragraph","text":"Group your spending into needs, wants and savings, then review the plan every month."}]'::jsonb
),
(
    'emergency-fund',
    'Emergency Funds: Why Cash Still Matters',
    'Before investing or taking bigger risks, many households keep a cash buffer.',
    'https://images.unsplash.com/photo-1579621970795-87facc2f976d?auto=format&fit=crop&w=900&q=80',
    'FinanceAI Learning Team',
    'Knowledge Base',
    'Saving',
    'published',
    '2026-06-28T14:00:00+10:00',
    1460,
    88,
    52,
    '[{"type":"paragraph","text":"An emergency fund is money set aside for expenses that cannot easily wait."},{"type":"paragraph","text":"Keep this money somewhere accessible and low risk."}]'::jsonb
),
(
    'investment-risk',
    'Risk and Diversification When You Start Investing',
    'Shares, bonds, cash and property behave differently. Diversification helps avoid relying on one outcome.',
    'https://images.unsplash.com/photo-1642543492481-44e81e3914a7?auto=format&fit=crop&w=900&q=80',
    'FinanceAI Learning Team',
    'Knowledge Base',
    'Investing',
    'published',
    '2026-05-30T12:30:00+10:00',
    2450,
    201,
    94,
    '[{"type":"paragraph","text":"Investment risk means the outcome may differ from what you expect."},{"type":"paragraph","text":"Diversification can reduce the effect of one poor outcome, but it does not remove risk."}]'::jsonb
)
ON CONFLICT (id) DO NOTHING;

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
