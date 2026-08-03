from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api import (
    routes_admin,
    routes_ai,
    routes_articles,
    routes_auth,
    routes_calculator,
    routes_chat,
    routes_financials,
    routes_goals,
    routes_memory,
    routes_profile,
    routes_rules,
)
from app.core.config import settings
from app.schemas.system import ApiIndexResponse, HealthResponse


API_VERSION = "0.2.0"

OPENAPI_TAGS = [
    {"name": "Auth", "description": "Registration, verification, sessions and account settings."},
    {"name": "Profile", "description": "Authenticated user's financial profile."},
    {"name": "Financials", "description": "Assets, debts, cash flows and dashboard summaries."},
    {"name": "Goals", "description": "Goal planning, progress, notifications and allocations."},
    {"name": "Articles", "description": "Published Knowledge Hub content and engagement."},
    {"name": "Long-term Memory", "description": "User-controlled context for personalised guidance."},
    {"name": "AI Advisor", "description": "Grounded chat, streaming and supported PDF analysis."},
    {"name": "Chat History", "description": "Persistent advisor conversations and messages."},
    {"name": "Calculator", "description": "Deterministic financial calculations."},
    {"name": "Rules", "description": "Versioned financial rules with source attribution."},
    {"name": "Admin", "description": "Administrator-only users, advisory settings and articles."},
    {"name": "System", "description": "API discovery and service health."},
]


app = FastAPI(
    title="AI Financial Literacy Advisor API",
    summary="Backend API for FinanceAI",
    description=(
        "Public article reads require no token. Personal endpoints require "
        "`Authorization: Bearer <access_token>`; Admin endpoints also require "
        "an account with the `admin` role."
    ),
    version=API_VERSION,
    openapi_tags=OPENAPI_TAGS,
)


# Create the upload directory if it does not exist.
Path(settings.upload_dir).mkdir(
    parents=True,
    exist_ok=True,
)


# Make uploaded files accessible through /uploads.
app.mount(
    "/uploads",
    StaticFiles(
        directory=settings.upload_dir,
    ),
    name="uploads",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_origin_regex=(
        r"http://("
        r"192\.168\.\d+\.\d+|"
        r"10\.\d+\.\d+\.\d+|"
        r"172\.(1[6-9]|2\d|3[0-1])\.\d+\.\d+"
        r"):5173"
    ),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(
    routes_auth.router,
    prefix="/api/auth",
    tags=["Auth"],
)

app.include_router(
    routes_financials.router,
    prefix="/api/financials",
    tags=["Financials"],
)

app.include_router(
    routes_articles.router,
    prefix="/api/articles",
    tags=["Articles"],
)

app.include_router(
    routes_chat.router,
    prefix="/api/chat",
    tags=["Chat History"],
)

app.include_router(
    routes_profile.router,
    prefix="/api/profile",
    tags=["Profile"],
)

app.include_router(
    routes_calculator.router,
    prefix="/api/calculator",
    tags=["Calculator"],
)

app.include_router(
    routes_rules.router,
    prefix="/api/rules",
    tags=["Rules"],
)

app.include_router(
    routes_ai.router,
    prefix="/api/ai",
    tags=["AI Advisor"],
)

app.include_router(
    routes_goals.router,
    prefix="/api/goals",
    tags=["Goals"],
)

app.include_router(
    routes_memory.router,
    prefix="/api/memory",
    tags=["Long-term Memory"],
)

app.include_router(
    routes_admin.router,
    prefix="/api/admin",
    tags=["Admin"],
)


@app.get(
    "/api",
    response_model=ApiIndexResponse,
    tags=["System"],
    summary="Discover API documentation and health endpoints",
)
def api_index():
    return {
        "name": app.title,
        "version": API_VERSION,
        "docs_url": "/docs",
        "openapi_url": "/openapi.json",
        "health_url": "/api/health",
        "groups": {
            "authentication": ["/api/auth"],
            "financials": ["/api/profile", "/api/financials", "/api/goals"],
            "advice": ["/api/rules", "/api/ai", "/api/chat", "/api/memory"],
            "knowledge_hub": ["/api/articles"],
            "administration": ["/api/admin/users", "/api/admin/articles"],
        },
    }


@app.get(
    "/api/health",
    response_model=HealthResponse,
    tags=["System"],
    summary="Check whether the API process is running",
)
def health_check():
    return {
        "status": "ok",
        "service": "financeai-api",
        "version": API_VERSION,
    }
