# API Contract

The running FastAPI OpenAPI document at `/openapi.json` and interactive UI at
`/docs` are the authoritative endpoint and schema references. This document
summarizes conventions and cross-endpoint workflows for frontend and backend
development.

All application routes use the `/api` prefix. Protected routes require
`Authorization: Bearer <access_token>`. Resource lookup is scoped to the
authenticated user; a missing resource and another user's resource both return
`404`. Successful deletion normally returns `204 No Content`.

## Discovery and health

- GET /api
- GET /api/health

`GET /api` returns the service name, current API version, documentation URLs,
and major endpoint groups. `GET /api/health` is suitable for container and
deployment health checks.

## Authentication and account lifecycle

- POST /api/auth/register
- POST /api/auth/register/verification-code
- POST /api/auth/email/verification-code
- POST /api/auth/login
- GET /api/auth/me
- POST /api/auth/heartbeat
- POST /api/auth/password-reset/request-code
- POST /api/auth/password-reset/verify-code
- POST /api/auth/password-reset/reset
- DELETE /api/auth/me

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
only public API that directly changes a goal's current amount; the older
`/contributions` routes are retired. Accepting an AI savings plan is an
internal atomic workflow: it creates the goals, applies confirmed one-off
allocations as progress, reserves their cash, and initializes the exact ongoing
monthly allocations shown in MyGoals.

`POST /api/goals/preview` accepts the selected category, target date, priority,
and raw `category_details`. It returns normalized goal fields plus goal analysis,
so category target formulas and feasibility calculations are not duplicated in
the frontend wizard.

`GET/PUT /api/goals/allocation-settings` is the single source of truth for
allocation ratios. Its response includes backend-calculated monthly net income,
allocatable, assigned and unassigned totals, plus each goal's monthly amount.
The monthly source uses sustainable ongoing income minus ongoing expenses; it
does not include one-off cash-flow components. Ratios retain enough precision
for confirmed cent-level monthly amounts to round-trip without drift.
The former `/monthly-allocation` write route is retired.

- GET /api/auth/ping
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
- POST /api/ai/chat/stream
- POST /api/ai/chat/pdf
- GET /api/memory
- GET /api/memory/{memory_id}
- POST /api/memory
- PUT /api/memory/{memory_id}
- DELETE /api/memory/{memory_id}
- GET /api/memory/export
- GET /api/goals/ping
- GET /api/admin/ping
- GET /api/admin/users (admin only)
- GET /api/admin/users/{id} (admin only)
- POST /api/admin/users (admin only)
- PATCH /api/admin/users/{id} (admin only)
- DELETE /api/admin/users/{id} (admin only)
- GET /api/admin/advisory-settings (admin only)
- PATCH /api/admin/advisory-settings (admin only)
- POST /api/auth/heartbeat (authenticated user)

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
- GET /api/financials/assets
- POST /api/financials/assets
- GET /api/financials/assets/{asset_id}
- PUT /api/financials/assets/{asset_id}
- DELETE /api/financials/assets/{asset_id}
- GET /api/financials/cash-buckets/{bucket_id}
- GET /api/financials/cash-flows
- POST /api/financials/cash-flows
- GET /api/financials/cash-flows/{cash_flow_id}
- PUT /api/financials/cash-flows/{cash_flow_id}
- DELETE /api/financials/cash-flows/{cash_flow_id}

## Chat history

- GET /api/chat/conversations
- GET /api/chat/conversations/{conversation_id}
- POST /api/chat/conversations
- POST /api/chat/conversations/{conversation_id}/messages
- DELETE /api/chat/conversations/{conversation_id}

`POST /api/ai/chat` accepts optional `conversation_id`, `rule_id`, and
`goal_id` fields.
When `conversation_id` is supplied, the user and assistant messages are saved.
When `goal_id` is supplied, the backend verifies that the goal belongs to the
current user, stores an authoritative goal card in the selected conversation,
and sends the goal values plus its code-calculated progress analysis to the AI
for an educational review.
For general rule questions without `rule_id`, the backend first asks the LLM
for a structured intent classification (`knowledge_base_status`,
`tax_brackets`, `tax_calculation`, `employer_super`,
`super_contribution_caps`, or `out_of_scope`). The backend then performs
database retrieval and tax calculations from verified rules before sending
grounded context back to the LLM for the final plain-English answer.
Relevant long-term memories are retrieved before the AI drafts a response.
The response includes `memory_updated` and `memory_update_count`. These fields
describe actual committed memory changes, so repeated unchanged facts report
`false` and `0`.

`POST /api/ai/chat/stream` accepts the same JSON body and runs the same chat
workflow. It returns newline-delimited JSON using `application/x-ndjson`:
zero or more `delta` events followed by one `done` event. Failures that happen
inside the streaming workflow, including validation and provider failures, are
returned as an in-band `error` event after the HTTP 200 stream has opened. The
`done` event includes `memory_updated` and `memory_update_count`, matching the
non-streaming response. The frontend uses these fields to show the
`Memory updated` notice only after a real memory change.
The frontend buffers received deltas and renders them incrementally without slowing
the provider connection or leaving long responses in a display queue
indefinitely.

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
Extracted income and expense transactions are also batched for a separate
structured ongoing-versus-one-off classification. The backend keeps the parsed
amount authoritative, treats missing or low-confidence classifications as
one-off, and stores the ongoing component in `cash_flows.ongoing_amount`.
The remainder of each recorded amount is its one-off component. This preserves
the statement's actual cash movement while preventing one-off income from being
presented as sustainable monthly capacity.

## Long-term memory

Memory requests use `fact` and `category`. Supported categories are `asset`,
`debt`, `expense`, `goal`, `income`, `preference`, `profile`, and `other`.
Responses include `source`, timestamps, and `last_used_at`. Users can export
all stored facts through `/api/memory/export`.

After a successful `/api/ai/chat` turn, the backend extracts durable facts from
the latest user message, recent conversation context, and the assistant reply.
This lets short answers inherit the subject of the preceding question and lets
personalized AI recommendations or confirmations become memory. A new value for
an existing subject updates that memory in place and removes older conflicting
duplicates. Memory extraction failure never prevents the completed chat reply
from being returned. Structured extraction receives only relevant candidate
memories instead of unrelated recent facts, reducing prompt size and the chance
of replacing an unrelated memory.

## Account deletion

- DELETE /api/auth/me with JSON body `{ "current_password": "..." }`

## Extended financials

- GET /api/financials/debts
- POST /api/financials/debts
- GET /api/financials/debts/{debt_id}
- PUT /api/financials/debts/{debt_id}
- DELETE /api/financials/debts/{debt_id}
- GET /api/financials/recurring-cash-flows
- POST /api/financials/recurring-cash-flows
- GET /api/financials/recurring-cash-flows/{id}
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
Cash-flow responses include `ongoing_amount`; manual one-off records default it
to zero. Goal-planning calculations use the latest classified ongoing
components as monthly capacity and derive one-off amounts as
`amount - ongoing_amount`. When the same flow type is also represented by an
active recurring schedule, the larger supported monthly total is used instead
of summing duplicate evidence.

## Knowledge Hub

Published content is available to authenticated users through the public
article API:

- GET /api/articles
- GET /api/articles/categories
- GET /api/articles/featured
- GET /api/articles/recommended
- GET /api/articles/{article_id}
- POST /api/articles/{article_id}/view
- POST /api/articles/{article_id}/like
- DELETE /api/articles/{article_id}/like
- POST /api/articles/{article_id}/save
- DELETE /api/articles/{article_id}/save
- GET /api/articles/me/liked
- GET /api/articles/me/saved

The article list accepts `keyword`, `category`, `sort_by`, `page`, and
`page_size`. Detail responses include article content, source metadata,
engagement totals, and the current user's helpful/bookmark state. Public routes
never expose draft or archived articles. Article source fields (`source_name`,
`source_url`, and `published_at`) are part of the API contract so references can
be rendered as usable links rather than embedded presentation-only text.

## Administration

All routes below require an administrator token.

### Users and advisory settings

- GET /api/admin/users
- POST /api/admin/users
- GET /api/admin/users/{user_id}
- PATCH /api/admin/users/{user_id}
- DELETE /api/admin/users/{user_id}
- GET /api/admin/advisory-settings
- PATCH /api/admin/advisory-settings

### Article lifecycle

- GET /api/admin/articles
- POST /api/admin/articles
- GET /api/admin/articles/{article_id}
- PUT /api/admin/articles/{article_id}
- DELETE /api/admin/articles/{article_id}
- POST /api/admin/articles/{article_id}/publish
- POST /api/admin/articles/{article_id}/unpublish

Unlike `/api/articles`, the admin list and detail endpoints expose all allowed
states (`draft`, `published`, and `archived`). The list supports `keyword`,
`category`, `status`, `sort_by`, `page`, and `page_size`, and returns pagination
metadata. This separation lets the admin frontend retrieve and edit drafts
without weakening the published-only public interface.
