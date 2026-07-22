# Initial API Contract

## Goals

- GET /api/goals
- POST /api/goals
- POST /api/goals/preview
- GET /api/goals/summary
- GET /api/goals/{goal_id}
- PUT /api/goals/{goal_id}
- DELETE /api/goals/{goal_id}
- GET /api/goals/{goal_id}/analysis
- GET /api/goals/{goal_id}/chart
- GET /api/goals/{goal_id}/progress
- POST /api/goals/{goal_id}/progress
- PUT /api/goals/{goal_id}/progress/{progress_id}
- DELETE /api/goals/{goal_id}/progress/{progress_id}
- GET /api/goals/allocation-settings
- PUT /api/goals/allocation-settings

Goal requests contain `name`, `category`, `target_amount`, `current_amount`,
`monthly_contribution`, `target_date`, and `priority` (1-5). Goal responses
include backend-calculated `status` and `progress_percentage`. Progress is the
only public API that changes a goal's current amount; the older
`/contributions` routes are retired.

`POST /api/goals/preview` accepts the selected category, target date, priority,
and raw `category_details`. It returns normalized goal fields plus goal analysis,
so category target formulas and feasibility calculations are not duplicated in
the frontend wizard.

`GET/PUT /api/goals/allocation-settings` is the single source of truth for
allocation ratios. Its response includes backend-calculated monthly net income,
allocatable, assigned and unassigned totals, plus each goal's monthly amount.
The former `/monthly-allocation` write route is retired.

- GET /api/health
- GET /api/auth/ping
- POST /api/auth/register/verification-code
- POST /api/auth/register
- POST /api/auth/login
- POST /api/auth/email/verification-code (authenticated user)
- PUT /api/auth/email (authenticated user)
- GET /api/profile/ping
- GET /api/calculator/ping
- GET /api/calculator/goal-monthly-saving?target_amount=10000&current_amount=1000&months=12
- GET /api/rules/ping
- GET /api/rules?region=Australia&category=tax&rule_year=2026-2027
- GET /api/rules/{rule_id}
- GET /api/rules/tax-bracket?region=Australia&rule_year=2026-2027&income=80000
- GET /api/rules/superannuation/employer-contribution?region=Australia&rule_year=2026-2027
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
- GET /api/admin/advisory-settings (admin only)
- PATCH /api/admin/advisory-settings (admin only)
- POST /api/auth/heartbeat (authenticated user)

Registration first sends a six-digit code to the requested email. The
registration request must include that code as `verification_code`. Changing
an authenticated user's login email follows the same pattern and also requires
the current password. Codes are single-use, expire after the configured TTL,
are rate-limited when resent, and are stored only as hashes.

Admin user requests use `first_name`, `last_name`, `email`, and `password`
for creation. Update requests omit `password`. User responses include `id`,
`user_id`, `created_at`, `is_online`, and `last_seen_at`.

Advisory settings return the canonical Budgeting, Saving, Tax,
Superannuation, Investing, and Debt topics. PATCH accepts one or more of
those topics with an `enabled` boolean, preserves omitted topic values, and
persists the resulting global configuration.

Before generating the final response for every `POST /api/ai/chat` request,
the backend reads the current global advisory settings and appends the enabled
and disabled topic lists to the AI system instruction. Settings are not cached,
so an admin update applies to the next chat request without a service restart.

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
signed transaction lines, and updates HomePage financial data. Monetary items
are sent to the LLM as numbered candidates for structured classification into
`cash`, `stocks`, `bonds`, `property`, `vehicle`, `others`, or `not_asset`.
The backend keeps the parsed `Decimal` amount as the source of truth, groups
accepted items by asset type and source PDF, and exposes those records through
the existing Asset Allocation summary. The LLM also explains the result in
plain English without Markdown formatting. Image-only PDFs are rendered for
OCR when the backend has PyMuPDF, pytesseract, Pillow, and the system
`tesseract` engine available. Low-confidence PDFs return a fallback response
without updating financial records.
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

## Extended financials

- GET /api/financials/debts
- POST /api/financials/debts
- PUT /api/financials/debts/{debt_id}
- DELETE /api/financials/debts/{debt_id}
- GET /api/financials/recurring-cash-flows
- POST /api/financials/recurring-cash-flows
- PUT /api/financials/recurring-cash-flows/{id}
- DELETE /api/financials/recurring-cash-flows/{id}

`GET /api/financials` includes assets, debts, one-off cash flows, and recurring
cash flows. The summary includes total assets, total debts, debt-adjusted net
worth, debt breakdown, and active recurring cash flows normalized to monthly
amounts. `cash_savings` is the cash-asset balance plus recorded one-off cash
flow net movement. Recurring cash flows affect `monthly_income` and
`monthly_expenses`, but do not change cash until a transaction is recorded.
`cash_savings_trend` contains six cumulative month-end balances calculated by
the backend. The current cash value is included in `total_assets` and
`asset_allocation`.
