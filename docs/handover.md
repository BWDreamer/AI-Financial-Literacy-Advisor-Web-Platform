# FinanceAI Handover Notes

This document summarises what has been delivered, how to run the system, what
credentials are required, and what the next maintainer should know.

## Delivered Components

### User-facing application

* Login, registration, email verification support, password reset, and
  role-based redirection.
* Homepage dashboard for net worth, cash savings, debt, income, expenses,
  asset allocation, monthly cash flow, saving summary, and recent cash flow.
* New-user onboarding card for collecting high-level preferences and optional
  financial snapshot information.
* Advisor Chat with AI financial education, verified rule context, long-term
  memory context, goal review context, and financial record context.
* My Goals module for creating, editing, tracking, and reviewing financial
  goals.
* Memory module for viewing, adding, editing, deleting, and exporting stored
  user facts.
* Knowledge Hub for article browsing, detail reading, categories, search,
  sorting, saved/liked filters, article statistics, rich article content, and
  recommendation behaviour linked to user memory.

### Admin application

* Admin dashboard with platform overview information.
* User management for inviting, editing, viewing, and deleting users.
* Advisory settings for configuring available advisor topics.
* Knowledge Hub management for creating, editing, deleting, and uploading
  article images.

### Backend and data

* FastAPI backend with JWT authentication and role-based access.
* PostgreSQL database with idempotent SQL migrations.
* Financial profile, financial records, goals, memory, articles, admin, rules,
  calculator, chat, and AI-related API routes.
* Docker Compose setup for frontend, backend, database, and migration runner.
* Backend and frontend test commands documented in the README.

## How to Run

From the project root:

```bash
cp .env.example .env
docker compose up --build
```

On Windows PowerShell:

```powershell
Copy-Item .env.example .env
docker compose up --build
```

Open:

* Frontend: http://localhost:5173
* Backend: http://localhost:8000
* API documentation: http://localhost:8000/docs
* Health check: http://localhost:8000/api/health

To run in the background:

```bash
docker compose up --build -d
```

To stop:

```bash
docker compose down
```

## Entry Points

* Public login and registration: http://localhost:5173/login
* Regular user dashboard: http://localhost:5173/home
* Advisor Chat: http://localhost:5173/advisor-chat
* My Goals: http://localhost:5173/goals
* Knowledge Hub: http://localhost:5173/knowledge-hub
* Admin console: http://localhost:5173/admin
* Admin Knowledge Hub: http://localhost:5173/admin/knowledge

## Demo Accounts

Real demo credentials should not be committed to the repository.

For local testing, create a regular user from the registration page. To create
a local admin account, add these values to `.env`:

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

If a handover demo account is prepared, send the email and password to the
client through a separate secure channel, not through GitHub.

## Required Secrets and Configuration

Create `.env` from `.env.example`. The most important values are:

| Area | Variables | Notes |
| --- | --- | --- |
| Database | `DATABASE_URL` | Docker Compose uses the bundled PostgreSQL service by default. |
| JWT | `JWT_SECRET_KEY`, `JWT_ALGORITHM`, `JWT_EXPIRE_MINUTES` | Use a strong secret outside local development. |
| AI provider | `LLM_PROVIDER`, `OPENROUTER_API_KEY`, `GEMINI_API_KEY`, `LLM_MODEL` | At least one valid provider key is required for live AI responses. |
| Email verification | `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM_EMAIL` | Required for sending verification and password reset emails. |
| Admin seed | `ADMIN_EMAIL`, `ADMIN_PASSWORD`, `ADMIN_NAME` | Used by `backend/scripts/create_admin.py`. |
| Uploads | `UPLOAD_DIR`, `MAX_UPLOAD_SIZE_MB` | Used for uploaded assets and PDFs. |

Do not commit real API keys, SMTP credentials, JWT secrets, or production
administrator passwords.

## Maintenance Notes

* Database migrations are run through the `migrate` service in
  `docker-compose.yml`.
* Existing local database data is kept in the Docker `postgres_data` volume.
  Use caution before deleting volumes, because this removes local data.
* The frontend communicates with the backend through
  `VITE_API_BASE_URL=http://localhost:8000/api` in Docker.
* Backend API documentation is available at `/docs` when the backend is
  running.
* Article images and upload files are stored through backend upload handling;
  production deployment should use persistent storage.
* AI behaviour can be tuned through the variables documented in
  `docs/runtime-configuration.md`.

## Known Limitations

* FinanceAI is an educational prototype and does not provide professional
  financial, investment, legal, or tax advice.
* Live AI responses depend on external provider availability and valid API
  credentials.
* Email verification depends on a configured SMTP account.
* The project currently does not include live bank-account integration or open
  banking connections.
* Financial data quality depends on what users enter or upload.
* Production use would require deployment hardening, HTTPS, monitoring,
  backups, stronger secret management, and production-grade storage.
* Some advanced financial recommendation logic remains rule/context based and
  should be validated further with real users.

## Future Work

* Production deployment on managed frontend, backend, and PostgreSQL services.
* CI/CD expansion for automated build, test, and deployment.
* More realistic demo data and seeded user journeys for client evaluation.
* More complete financial data import and transaction categorisation.
* Stronger Knowledge Hub recommendation ranking using user memory, goals, and
  reading history.
* Expanded admin analytics for article performance and user engagement.
* More user testing with students and early-career workers.
* Security review for production secrets, authentication flows, upload
  handling, and data retention.

## Handover Checklist

Before final handover, confirm that the client has:

* Repository access or a zipped copy of the final code.
* README and this handover document.
* `.env.example` and separate real credentials/secrets where required.
* Admin account details or instructions to create an admin account.
* Local run command and confirmed application URLs.
* API documentation link.
* Known limitations and future work list.
* Any required screenshots or meeting notes.
* Confirmation email or message showing the client received the handover
  materials.
