# AI Financial Literacy Advisor Web Platform

This repository contains the initial project scaffold for the AI Financial Literacy Advisor Web Platform.

## Tech Stack

- Frontend: React + Vite + TypeScript
- Backend: FastAPI
- Database: PostgreSQL
- Containerisation: Docker + Docker Compose
- Authentication: JWT
- AI Service: controlled backend AI service layer

## Run Locally with Docker

```bash
cp .env.example .env
docker compose up --build
```

Frontend: http://localhost:5173

Backend health check: http://localhost:8000/api/health

FastAPI docs: http://localhost:8000/docs

## Development Rules

- The frontend must not call the database or LLM API directly.
- All user data, AI requests, uploads and admin actions must go through authenticated backend APIs.
- User and Admin permissions must be checked on the backend.
- Financial calculations should be performed by deterministic backend code, not directly by the LLM.
