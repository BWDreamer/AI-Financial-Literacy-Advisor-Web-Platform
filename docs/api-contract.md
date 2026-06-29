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
