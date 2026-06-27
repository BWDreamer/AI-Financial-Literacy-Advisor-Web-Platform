# AI Financial Literacy Advisor Web Platform

This project is an AI Financial Literacy Advisor Web Platform developed for COMP9900.

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
GET /api/rules/tax-bracket?region=Australia&rule_year=2025-2026&income=80000
GET /api/rules/superannuation/employer-contribution?region=Australia&rule_year=2025-2026
```

Detailed request and response formats are available in the FastAPI documentation:

```text
http://localhost:8000/docs
```

## Run Backend Tests

Run all backend tests:

```bash
docker compose exec backend pytest -q
```

The current backend test suite covers authentication, financial profiles, calculators and financial-rule queries.

## Development Notes

* The frontend must not connect directly to PostgreSQL.
* Database operations must go through backend APIs.
* Passwords must not be stored as plain text.
* Secrets must be stored in `.env`.
* Financial calculations should be handled by backend code rather than the AI model.
* Team members should develop on separate feature branches.
