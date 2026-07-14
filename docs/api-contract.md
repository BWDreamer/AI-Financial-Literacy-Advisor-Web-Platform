# Initial API Contract

## Goals

- GET /api/goals
- POST /api/goals
- GET /api/goals/summary
- GET /api/goals/{goal_id}
- PUT /api/goals/{goal_id}
- DELETE /api/goals/{goal_id}
- POST /api/goals/{goal_id}/contributions
- GET /api/goals/{goal_id}/contributions

Goal requests contain `name`, `category`, `target_amount`, `current_amount`,
`monthly_contribution`, `target_date`, and `priority` (1-5). Contribution
requests contain a positive `amount`.

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
- POST /api/ai/chat/pdf
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
For general rule questions without `rule_id`, the backend first asks the LLM
for a structured intent classification (`knowledge_base_status`,
`tax_brackets`, `tax_calculation`, `employer_super`,
`super_contribution_caps`, or `out_of_scope`). The backend then performs
database retrieval and tax calculations from verified rules before sending
grounded context back to the LLM for the final plain-English answer.
Relevant long-term memories are retrieved before the AI drafts a response.

`POST /api/ai/chat/pdf` accepts multipart form data with `message`,
`conversation_id`, and one or more `files`. It supports text-based PDFs,
extracts supported financial fields, calculates income and expenses from
signed transaction lines, updates HomePage financial basics, and uses the LLM
to explain the result in plain English without Markdown formatting. Image-only
PDFs are rendered for OCR when the backend has PyMuPDF, pytesseract, Pillow,
and the system `tesseract` engine available. Low-confidence PDFs return a
fallback response without updating financial records.
Ambiguous unsigned transaction lines are batched into one LLM structured
classification request. The LLM classifies direction and transaction type only;
amount extraction, validation, totals, and database writes remain backend
responsibilities.

## Long-term memory

Memory requests use `fact` and `category`. Supported categories are `asset`,
`debt`, `expense`, `goal`, `income`, `preference`, `profile`, and `other`.
Responses include `source`, timestamps, and `last_used_at`. Users can export
all stored facts through `/api/memory/export`.

## Account deletion

- DELETE /api/auth/me with JSON body `{ "current_password": "..." }`
