# FinanceAI — AI Financial Literacy Advisor

FinanceAI is a full-stack financial education and planning platform developed for COMP9900. It combines deterministic financial calculations and verified rules with an AI assistant, personal goals, financial tracking, and a managed Knowledge Hub.

## Features

- JWT authentication, email verification, password reset, role-based access, and online status tracking
- Financial profile, assets, cash buckets, debts, one-off cash flows, and recurring cash flows
- Savings goals, feasibility previews, progress history, charts, allocation settings, notifications, and archiving
- AI chat with streaming NDJSON responses, conversation history, long-term memory, and PDF statement extraction
- Source-backed tax and superannuation rules; calculations remain in backend code rather than the LLM
- Knowledge Hub articles with public search, filtering, sorting, pagination, reactions, bookmarks, and reading history
- Admin management for users, advisory settings, and draft/published/archived articles
- Automated backend and frontend tests

## Technology

| Layer | Technology |
| --- | --- |
| Frontend | React, TypeScript, Vite, Tailwind CSS |
| Backend | FastAPI, SQLAlchemy, Pydantic |
| Database | PostgreSQL |
| Authentication | JWT bearer tokens |
| AI | Configurable LLM provider, streamed and non-streamed chat |
| Deployment | Docker and Docker Compose |
| Testing | Pytest and Jest |

## Quick start

Requirements: Docker Desktop with Docker Compose.

```bash
cp .env.example .env
docker compose up --build
```

Startup waits for PostgreSQL, applies idempotent migrations to new or existing volumes, and then starts the API and frontend. Keep provider keys and credentials only in the untracked `.env` file. Runtime AI settings and validated ranges are documented in [`docs/runtime-configuration.md`](docs/runtime-configuration.md).

Useful commands:

```bash
docker compose up --build -d
docker compose logs -f backend
docker compose down
```

## Local services

- Frontend: <http://localhost:5173>
- API index: <http://localhost:8000/api>
- Interactive API documentation: <http://localhost:8000/docs>
- OpenAPI schema: <http://localhost:8000/openapi.json>
- Health check: <http://localhost:8000/api/health>

The port values can be overridden in `.env`. FastAPI's OpenAPI document is the authoritative, executable interface reference; [`docs/api-contract.md`](docs/api-contract.md) explains the main workflows and conventions.

## Calling the API

All application endpoints use the `/api` prefix and JSON unless noted otherwise. Register or log in, then send the returned token as a bearer credential:

```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"your-password"}'

curl http://localhost:8000/api/financials \
  -H "Authorization: Bearer <access_token>"
```

The API uses standard status codes: `200/201` for success, `204` for a successful deletion, `400/422` for invalid input, `401` for missing or invalid authentication, `403` for insufficient role, and `404` for an inaccessible resource.

## API groups

| Group | Base path | Purpose |
| --- | --- | --- |
| Authentication | `/api/auth` | Registration, verification, login, password reset, account lifecycle |
| Profile | `/api/profile` | Personal and financial profile |
| Financials | `/api/financials` | Assets, buckets, debts, cash flows, recurring flows, summaries |
| Goals | `/api/goals` | Goal planning, progress, analysis, charts, allocations, notifications |
| Rules | `/api/rules` | Verified financial rules and backend calculations |
| AI and chat | `/api/ai`, `/api/chat` | AI advice, streaming, PDF input, persisted conversations |
| Memory | `/api/memory` | User-managed long-term AI facts and export |
| Knowledge Hub | `/api/articles` | Published articles, engagement, bookmarks, reading history |
| Administration | `/api/admin` | Users, advisory settings, and complete article lifecycle |

Collection and item endpoints are both available for core resources. Examples include `GET /api/financials/assets` and `GET /api/financials/assets/{asset_id}`, plus equivalent routes for cash flows, cash buckets, debts, recurring cash flows, memories, articles, and admin users. Item access is ownership-checked and normally returns `404` rather than revealing another user's data.

## Knowledge Hub management

Public users read only published articles through `/api/articles`. Administrators use separate endpoints so drafts and archived content remain manageable:

```text
GET    /api/admin/articles
POST   /api/admin/articles
GET    /api/admin/articles/{article_id}
PUT    /api/admin/articles/{article_id}
DELETE /api/admin/articles/{article_id}
POST   /api/admin/articles/{article_id}/publish
POST   /api/admin/articles/{article_id}/unpublish
```

The admin list supports `keyword`, `category`, `status`, `sort_by`, `page`, and `page_size`. Public article responses expose citation fields such as source name, source URL, and publication date so the frontend can present references clearly.

## Create a local administrator

Set credentials in `.env`:

```text
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=replace_with_a_secure_password
ADMIN_NAME=Admin
```

Then run the idempotent setup script:

```bash
docker compose up -d db backend
docker compose exec backend python scripts/create_admin.py
```

Running it again does not create a duplicate. An existing regular account with that email is upgraded to admin and receives the configured password. Never commit `.env` or real credentials.

## Tests and coverage

```bash
# Backend
docker compose exec backend pytest -q
docker compose exec backend pytest --cov=app --cov-report=term-missing --cov-report=html

# Frontend
docker compose exec frontend npm test -- --runInBand
docker compose exec frontend npm run test:coverage
```

Generated reports are written to `backend/htmlcov/` and `frontend/coverage/`.

## Project structure

```text
backend/              FastAPI application and tests
frontend/             React application and tests
database/             Initial schema and ordered migrations
docs/                 API, architecture, deployment, and runtime documentation
docker-compose.yml    Local service orchestration
```

The frontend communicates with PostgreSQL only through the backend API. Passwords are hashed, secrets stay in environment variables, and authoritative financial calculations are implemented and tested in backend code.
