CREATE TABLE IF NOT EXISTS advisory_settings (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    topics JSONB NOT NULL CHECK (jsonb_typeof(topics) = 'array'),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO advisory_settings (id, topics)
VALUES (
    1,
    '[
        {"name": "Budgeting", "enabled": true},
        {"name": "Saving", "enabled": true},
        {"name": "Tax", "enabled": true},
        {"name": "Superannuation", "enabled": true},
        {"name": "Investing", "enabled": false},
        {"name": "Debt", "enabled": true}
    ]'::jsonb
)
ON CONFLICT (id) DO NOTHING;
