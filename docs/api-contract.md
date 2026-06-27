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
