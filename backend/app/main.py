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


app = FastAPI(
    title="AI Financial Literacy Advisor API",
    version="0.1.0",
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


@app.get("/api/health")
def health_check():
    return {
        "status": "ok",
    }
