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
    '[{"type":"paragraph","text":"A useful budget starts with the money that actually arrives in your account and the spending that actually leaves it."},{"type":"image","src":"https://images.unsplash.com/photo-1554224154-26032ffc0d07?auto=format&fit=crop&w=1200&q=80","alt":"A person reviewing household budget notes and receipts","caption":"Start with real spending records before setting a monthly target."},{"type":"paragraph","text":"Group your spending into needs, wants and savings, then review the plan every month."}]'::jsonb
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
    '[{"type":"paragraph","text":"An emergency fund is money set aside for expenses that cannot easily wait."},{"type":"paragraph","text":"Keep this money somewhere accessible and low risk. The goal is availability, not high return."}]'::jsonb
),
(
    'compound-interest',
    'Compound Interest Without the Jargon',
    'Understand how time, return and regular contributions can change long-term savings outcomes.',
    'https://images.unsplash.com/photo-1520607162513-77705c0f0d4a?auto=format&fit=crop&w=900&q=80',
    'FinanceAI Learning Team',
    'Knowledge Base',
    'Saving',
    'published',
    '2026-06-20T10:00:00+10:00',
    2130,
    154,
    67,
    '[{"type":"paragraph","text":"Compound interest means earning interest on both your original money and the interest already earned."},{"type":"image","src":"https://images.unsplash.com/photo-1551288049-bebda4e38f71?auto=format&fit=crop&w=1200&q=80","alt":"A financial chart showing growth over time","caption":"Compound growth is easiest to understand when comparing different time horizons."}]'::jsonb
),
(
    'marginal-tax',
    'Marginal Tax Rates: What They Actually Mean',
    'Only part of your income is taxed at each bracket rate.',
    'https://images.unsplash.com/photo-1450101499163-c8848c66ca85?auto=format&fit=crop&w=900&q=80',
    'FinanceAI Learning Team',
    'Knowledge Base',
    'Tax',
    'published',
    '2026-06-16T16:45:00+10:00',
    1210,
    97,
    34,
    '[{"type":"paragraph","text":"A marginal tax system divides income into layers, with each layer taxed at its own rate."},{"type":"paragraph","text":"Use official sources or professional advice for decisions; this article is educational."}]'::jsonb
),
(
    'super-basics',
    'Superannuation Basics for New Workers',
    'A beginner-friendly explanation of employer contributions and long-term retirement savings.',
    'https://images.unsplash.com/photo-1565514020179-026b92b84bb6?auto=format&fit=crop&w=900&q=80',
    'FinanceAI Learning Team',
    'Knowledge Base',
    'Superannuation',
    'published',
    '2026-06-08T13:10:00+10:00',
    980,
    76,
    29,
    '[{"type":"paragraph","text":"Superannuation is designed to help people save for retirement during their working life."},{"type":"paragraph","text":"Because super is long term, fees, insurance settings and investment options may matter over time."}]'::jsonb
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
),
(
    'scam-safety',
    'How to Spot Common Financial Scam Signals',
    'Pressure, secrecy and guaranteed returns are warning signs.',
    'https://images.unsplash.com/photo-1563986768609-322da13575f3?auto=format&fit=crop&w=900&q=80',
    'FinanceAI Learning Team',
    'Knowledge Base',
    'Security',
    'published',
    '2026-05-21T15:20:00+10:00',
    1675,
    132,
    58,
    '[{"type":"paragraph","text":"Financial scams often create urgency or secrecy."},{"type":"paragraph","text":"Pause before clicking links, sharing codes or sending money under pressure."}]'::jsonb
)
ON CONFLICT (id) DO NOTHING;
