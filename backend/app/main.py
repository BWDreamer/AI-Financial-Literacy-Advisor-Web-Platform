from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import routes_auth, routes_profile, routes_calculator, routes_rules, routes_ai, routes_goals, routes_admin

app = FastAPI(title="AI Financial Literacy Advisor API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(routes_auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(routes_profile.router, prefix="/api/profile", tags=["Profile"])
app.include_router(routes_calculator.router, prefix="/api/calculator", tags=["Calculator"])
app.include_router(routes_rules.router, prefix="/api/rules", tags=["Rules"])
app.include_router(routes_ai.router, prefix="/api/ai", tags=["AI Advisor"])
app.include_router(routes_goals.router, prefix="/api/goals", tags=["Goals"])
app.include_router(routes_admin.router, prefix="/api/admin", tags=["Admin"])

@app.get("/api/health")
def health_check():
    return {"status": "ok"}
