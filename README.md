# AI Financial Literacy Advisor Web Platform

This project is an AI Financial Literacy Advisor Web Platform developed for COMP9900.

## Handover Summary

FinanceAI is a responsive financial literacy web platform for everyday money
education and planning. It combines a user dashboard, AI advisor, long-term
memory, goal planning, educational articles, and an admin console for platform
management.

### Main Modules

* Authentication: user registration, login, password reset, JWT sessions, and
  role-based navigation.
* Homepage dashboard: financial overview for cash savings, income, expenses,
  debt, net worth, asset allocation, monthly cash flow, and recent cash flow.
* New-user onboarding: a lightweight setup flow that captures user preferences
  and optional financial snapshot information.
* Advisor Chat: AI-supported financial education with memory, financial
  records, goals, and verified rule context.
* My Goals: goal creation, editing, progress tracking, allocation summaries,
  and AI goal review support.
* Memory: user-managed long-term facts and preferences that can be reused by
  the advisor.
* Knowledge Hub: article browsing, detail pages, categories, search, sorting,
  saved/liked views, rich article content, and personalised recommendations.
* Admin Console: admin dashboard, user management, advisory settings, and
  Knowledge Hub article management.

### User and Admin Entry Points

* Public login and registration: http://localhost:5173/login
* Regular user area after login: http://localhost:5173/home
* User Knowledge Hub: http://localhost:5173/knowledge-hub
* Admin console after admin login: http://localhost:5173/admin
* Admin Knowledge Hub management: http://localhost:5173/admin/knowledge
* Backend API documentation: http://localhost:8000/docs

### Demo Accounts

This repository does not commit real demo credentials. For local handover or
assessment, create a regular user through the registration page, then create a
local admin account from `.env`:

```text
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=replace_with_a_secure_password
ADMIN_NAME=Admin
```

Then run:

```bash
docker compose up -d db backend
docker compose exec backend python scripts/create_admin.py
```

Send any real demo account credentials to the client or tutor separately from
the GitHub repository.

### AI and Email Configuration

The application can run locally without real AI or SMTP credentials, but some
features will be unavailable:

* AI advisor responses require either `OPENROUTER_API_KEY` or `GEMINI_API_KEY`.
* Email verification and password reset emails require SMTP settings such as
  `SMTP_HOST`, `SMTP_USERNAME`, `SMTP_PASSWORD`, and `SMTP_FROM_EMAIL`.

Use `.env.example` as the template and place real secrets only in the untracked
local `.env` file. Do not commit API keys, SMTP credentials, or real admin
passwords.

### Known Issues and Limitations

* The AI advisor provides financial education and planning support only. It
  must not be treated as professional financial, investment, legal, or tax
  advice.
* AI and email features depend on external provider credentials configured in
  `.env`.
* Local Docker data is stored in the `postgres_data` volume. Existing local
  data remains unless the volume is explicitly removed.
* The project is a course prototype. Production deployment would require
  stronger secret management, monitoring, backups, HTTPS configuration, and
  production database hosting.
* Bank-account integration is not included. Users provide financial information
  through manual entry and supported PDF upload flows.

For a client handover checklist, see [`docs/handover.md`](docs/handover.md).

## Tech Stack

* Frontend: React, Vite and TypeScript
* Backend: FastAPI
* Database: PostgreSQL
* Authentication: JWT
* Containerisation: Docker and Docker Compose
* Testing: Pytest

## Run the Project

Create the local environment file:

```bash
cp .env.example .env
```

Start the project:

```bash
docker compose up --build
```

Startup waits for PostgreSQL to become healthy, applies the idempotent SQL
migrations to both new and existing data volumes, and then starts the backend.
Existing local data does not need to be deleted when a new migration is added.
AI runtime tuning variables and validated ranges are documented in
[`docs/runtime-configuration.md`](docs/runtime-configuration.md).
OpenRouter is supported through `LLM_PROVIDER=openrouter`; keep its API key only
in the untracked local `.env` file.

Run the project in the background:

```bash
docker compose up --build -d
```

Stop the project:

```bash
docker compose down
```

## Local Addresses

* Frontend: http://localhost:5173
* Backend: http://localhost:8000
* API documentation: http://localhost:8000/docs
* Health check: http://localhost:8000/api/health

## Implemented Backend Features

* User registration
* Password hashing
* User login
* JWT authentication
* Current-user retrieval
* Financial profile creation, retrieval and update
* Compound-interest calculation
* Savings-goal calculation
* Financial-rules listing and filtering
* Structured ATO tax-bracket and superannuation rule lookup
* Long-term AI memory with user-managed financial facts
* PostgreSQL data storage
* Automated backend tests

## Main API Endpoints

### Authentication

```text
POST /api/auth/register
POST /api/auth/login
GET  /api/auth/me
```

### Financial Profile

```text
GET /api/profile
PUT /api/profile
```

### Financial Calculators

```text
POST /api/calculator/compound-interest
POST /api/calculator/goal-monthly-saving
```

### Financial Rules

```text
GET /api/rules
GET /api/rules/{rule_id}
GET /api/rules/tax-bracket?region=Australia&rule_year=2026-2027&income=80000
GET /api/rules/superannuation/employer-contribution?region=Australia&rule_year=2026-2027
```

### Long-term Memory

```text
GET    /api/memory
POST   /api/memory
PUT    /api/memory/{memory_id}
DELETE /api/memory/{memory_id}
GET    /api/memory/export
```

Detailed request and response formats are available in the FastAPI documentation:

```text
http://localhost:8000/docs
```

## Run Tests and Coverage

Run all backend tests:

```bash
docker compose exec backend pytest -q
```

Run backend tests with coverage:

```bash
docker compose exec backend pytest --cov=app --cov-report=term-missing --cov-report=html
```

Open the backend HTML coverage report:

```bash
open backend/htmlcov/index.html
```

Run frontend tests with coverage:

```bash
docker compose exec frontend npm run test:coverage
```

Open the frontend HTML coverage report:

```bash
open frontend/coverage/lcov-report/index.html
```



## Create a Local Administrator

Add local administrator details to `.env`:

```text
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=replace_with_a_secure_password
ADMIN_NAME=Admin
```

Start the database and backend, then run the idempotent creation script:

```bash
docker compose up -d db backend
docker compose exec backend python scripts/create_admin.py
```

Running the script again will not create a duplicate account. If the email
belongs to a regular user, that user is upgraded to `role="admin"` and the
configured password is applied. For a local Python environment, run this from
the project root so the root `.env` file is loaded:

```bash
python backend/scripts/create_admin.py
```

Do not commit `.env` or real administrator credentials.

## Development Notes

* The frontend must not connect directly to PostgreSQL.
* Database operations must go through backend APIs.
* Passwords must not be stored as plain text.
* Secrets must be stored in `.env`.
* Financial calculations should be handled by backend code rather than the AI model.
* Team members should develop on separate feature branches.
