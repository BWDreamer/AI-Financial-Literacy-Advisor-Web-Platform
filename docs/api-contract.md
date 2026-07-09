# Initial API Contract

- GET /api/health
- GET /api/auth/ping
- GET /api/profile/ping
- GET /api/calculator/ping
- GET /api/calculator/goal-monthly-saving?target_amount=10000&current_amount=1000&months=12
- GET /api/rules/ping
- GET /api/rules?region=Australia&category=tax&rule_year=2025-2026
- GET /api/rules/{rule_id}
- GET /api/rules/tax-bracket?region=Australia&rule_year=2025-2026&income=80000
- GET /api/rules/superannuation/employer-contribution?region=Australia&rule_year=2025-2026
- GET /api/ai/ping
- POST /api/ai/chat
- GET /api/memory
- POST /api/memory
- PUT /api/memory/{memory_id}
- DELETE /api/memory/{memory_id}
- GET /api/memory/export
- GET /api/goals/ping
- GET /api/admin/ping
- GET /api/admin/users (admin only)
- POST /api/admin/users (admin only)
- PATCH /api/admin/users/{id} (admin only)
- DELETE /api/admin/users/{id} (admin only)
- POST /api/auth/heartbeat (authenticated user)

Admin user requests use `first_name`, `last_name`, `email`, and `password`
for creation. Update requests omit `password`. User responses include `id`,
`user_id`, `created_at`, `is_online`, and `last_seen_at`.

## Financials

- GET /api/financials
- GET /api/financials/summary
- POST /api/financials/assets
- PUT /api/financials/assets/{asset_id}
- DELETE /api/financials/assets/{asset_id}
- POST /api/financials/cash-flows
- PUT /api/financials/cash-flows/{cash_flow_id}
- DELETE /api/financials/cash-flows/{cash_flow_id}

## Chat history

- GET /api/chat/conversations
- GET /api/chat/conversations/{conversation_id}
- POST /api/chat/conversations
- POST /api/chat/conversations/{conversation_id}/messages
- DELETE /api/chat/conversations/{conversation_id}

`POST /api/ai/chat` accepts optional `conversation_id` and `rule_id` fields.
When `conversation_id` is supplied, the user and assistant messages are saved.
Relevant long-term memories are retrieved before the AI drafts a response.

## Long-term memory

Memory requests use `fact` and `category`. Supported categories are `asset`,
`debt`, `expense`, `goal`, `income`, `preference`, `profile`, and `other`.
Responses include `source`, timestamps, and `last_used_at`. Users can export
all stored facts through `/api/memory/export`.

## Account deletion

- DELETE /api/auth/me with JSON body `{ "current_password": "..." }`
