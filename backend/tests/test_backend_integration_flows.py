from datetime import date, datetime, timedelta, timezone

from app.ai.dependencies import get_ai_advisor_service
from app.core.security import hash_password
from app.main import app
from app.models.article import Article
from app.models.user import User


def create_user(client, db_session, email: str, role: str = "user") -> User:
    user = User(
        email=email,
        username=email.split("@")[0],
        password_hash=hash_password("Password123"),
        role=role,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def auth_headers(client, db_session, email: str, role: str = "user") -> dict[str, str]:
    create_user(client, db_session, email, role)
    response = client.post(
        "/api/auth/login",
        json={"email": email, "password": "Password123"},
    )
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def create_article(db_session, article_id: str, status: str = "published") -> None:
    db_session.add(
        Article(
            id=article_id,
            title=f"{article_id} title",
            summary="Short educational summary.",
            cover_image_url="https://example.com/cover.jpg",
            author_name="FinanceAI Learning Team",
            source_name="Knowledge Base",
            category="Budgeting",
            status=status,
            published_at=datetime(2026, 7, 2, tzinfo=timezone.utc),
            content_blocks=[{"type": "paragraph", "text": "Article body."}],
        )
    )
    db_session.commit()


def goal_payload(**overrides) -> dict:
    data = {
        "name": "Emergency fund",
        "category": "savings",
        "target_amount": "10000.00",
        "current_amount": "1000.00",
        "monthly_contribution": "500.00",
        "target_date": (date.today() + timedelta(days=365)).isoformat(),
        "priority": 1,
    }
    data.update(overrides)
    return data


class CapturingAdvisorService:
    model = "test-model"

    def __init__(self) -> None:
        self.messages: list[str] = []
        self.system_instructions: list[str | None] = []

    async def reply_json(self, message: str, response_schema: dict) -> dict:
        del message, response_schema
        return {
            "intent": "out_of_scope",
            "rule_year": None,
            "taxable_income": None,
            "confidence": 0.0,
        }

    async def reply(
        self,
        message: str,
        system_instruction: str | None = None,
    ) -> str:
        self.messages.append(message)
        self.system_instructions.append(system_instruction)
        return "Educational response."


def test_admin_user_list_includes_cross_module_engagement_counts(client, db_session):
    admin_headers = auth_headers(client, db_session, "admin-counts@example.com", "admin")
    user_headers = auth_headers(client, db_session, "engaged-user@example.com")
    user = db_session.query(User).filter(User.email == "engaged-user@example.com").one()
    create_article(db_session, "budgeting")
    create_article(db_session, "saving")

    client.put(
        "/api/profile",
        headers=user_headers,
        json={
            "region": "NSW",
            "monthly_income": 5000,
            "fixed_expenses": 2200,
            "current_savings": 10000,
            "initial_savings_target": 20000,
        },
    )
    client.post("/api/goals", headers=user_headers, json=goal_payload(name="First goal"))
    client.post("/api/goals", headers=user_headers, json=goal_payload(name="Second goal"))
    client.post("/api/articles/budgeting/like", headers=user_headers)
    client.post("/api/articles/budgeting/save", headers=user_headers)
    client.post("/api/articles/saving/save", headers=user_headers)

    response = client.get("/api/admin/users", headers=admin_headers)

    assert response.status_code == 200
    listed_user = next(item for item in response.json() if item["id"] == user.id)
    assert listed_user["region"] == "NSW"
    assert listed_user["goals_count"] == 2
    assert listed_user["liked_articles_count"] == 1
    assert listed_user["saved_articles_count"] == 2


def test_admin_delete_user_invalidates_access_to_owned_records(client, db_session):
    admin_headers = auth_headers(client, db_session, "admin-delete@example.com", "admin")
    user_headers = auth_headers(client, db_session, "delete-target@example.com")
    user = db_session.query(User).filter(User.email == "delete-target@example.com").one()
    create_article(db_session, "cascade-article")

    client.put(
        "/api/profile",
        headers=user_headers,
        json={
            "region": "VIC",
            "monthly_income": 6000,
            "fixed_expenses": 3000,
            "current_savings": 5000,
            "initial_savings_target": 15000,
        },
    )
    client.post(
        "/api/financials/assets",
        headers=user_headers,
        json={"asset_type": "cash", "name": "Savings", "amount": "5000.00"},
    )
    client.post(
        "/api/financials/debts",
        headers=user_headers,
        json={"debt_type": "credit_card", "name": "Card", "balance": "1000.00"},
    )
    client.post(
        "/api/financials/cash-flows",
        headers=user_headers,
        json={
            "flow_type": "income",
            "name": "Salary",
            "amount": "6000.00",
            "date": date.today().isoformat(),
        },
    )
    client.post(
        "/api/financials/recurring-cash-flows",
        headers=user_headers,
        json={
            "flow_type": "expense",
            "name": "Rent",
            "amount": "2000.00",
            "frequency": "monthly",
            "start_date": date.today().isoformat(),
        },
    )
    client.post(
        "/api/financials/cash-buckets",
        headers=user_headers,
        json={"bucket_type": "goal_reserved", "name": "Reserve", "amount": "500.00"},
    )
    goal_id = client.post(
        "/api/goals",
        headers=user_headers,
        json=goal_payload(),
    ).json()["id"]
    client.post(
        f"/api/goals/{goal_id}/progress",
        headers=user_headers,
        json={"amount": "100.00", "progress_date": date.today().isoformat()},
    )
    client.put(
        "/api/goals/allocation-settings",
        headers=user_headers,
        json={
            "cash_allocatable_ratio": "50",
            "monthly_allocatable_ratio": "20",
            "goal_monthly_ratios": [{"goal_id": goal_id, "ratio": "100"}],
        },
    )
    client.post(
        "/api/memory",
        headers=user_headers,
        json={"category": "preference", "fact": "I prefer cautious advice."},
    )
    conversation_id = client.post(
        "/api/chat/conversations",
        headers=user_headers,
        json={},
    ).json()["conversation_id"]
    client.post(
        f"/api/chat/conversations/{conversation_id}/messages",
        headers=user_headers,
        json={"role": "user", "content": "Remember this."},
    )
    client.post("/api/articles/cascade-article/like", headers=user_headers)
    client.post("/api/articles/cascade-article/save", headers=user_headers)

    response = client.delete(f"/api/admin/users/{user.id}", headers=admin_headers)

    assert response.status_code == 204
    assert client.get("/api/auth/me", headers=user_headers).status_code == 401
    listed_users = client.get("/api/admin/users", headers=admin_headers).json()
    assert all(item["id"] != user.id for item in listed_users)


def test_ai_chat_uses_latest_admin_advisory_settings(client, db_session):
    admin_headers = auth_headers(client, db_session, "admin-ai@example.com", "admin")
    user_headers = auth_headers(client, db_session, "ai-user@example.com")
    service = CapturingAdvisorService()
    app.dependency_overrides[get_ai_advisor_service] = lambda: service

    try:
        client.patch(
            "/api/admin/advisory-settings",
            headers=admin_headers,
            json={
                "topics": [
                    {"name": "Tax", "enabled": False},
                    {"name": "Investing", "enabled": True},
                ]
            },
        )
        response = client.post(
            "/api/ai/chat",
            headers=user_headers,
            json={"message": "What is compound interest?"},
        )
    finally:
        app.dependency_overrides.pop(get_ai_advisor_service, None)

    assert response.status_code == 200
    assert service.system_instructions
    system_instruction = service.system_instructions[-1]
    assert system_instruction is not None
    assert "Enabled topics" in system_instruction
    assert "Investing" in system_instruction
    assert "Disabled topics" in system_instruction
    assert "Tax" in system_instruction


def test_ai_chat_persists_user_and_assistant_messages(client, db_session):
    user_headers = auth_headers(client, db_session, "ai-history@example.com")
    service = CapturingAdvisorService()
    app.dependency_overrides[get_ai_advisor_service] = lambda: service

    try:
        conversation = client.post(
            "/api/chat/conversations",
            headers=user_headers,
            json={},
        ).json()
        response = client.post(
            "/api/ai/chat",
            headers=user_headers,
            json={
                "message": "Explain compound interest.",
                "conversation_id": conversation["conversation_id"],
            },
        )
        detail = client.get(
            f"/api/chat/conversations/{conversation['conversation_id']}",
            headers=user_headers,
        )
    finally:
        app.dependency_overrides.pop(get_ai_advisor_service, None)

    assert response.status_code == 200
    assert detail.status_code == 200
    messages = detail.json()["messages"]
    assert [message["role"] for message in messages] == ["user", "assistant"]
    assert messages[0]["content"] == "Explain compound interest."
    assert messages[1]["content"] == "Educational response."


def test_pdf_upload_validation_errors(client, db_session, monkeypatch):
    headers = auth_headers(client, db_session, "pdf-validation@example.com")
    conversation_id = client.post(
        "/api/chat/conversations",
        headers=headers,
        json={},
    ).json()["conversation_id"]

    assert client.post(
        "/api/ai/chat/pdf",
        headers=headers,
        data={"message": "Read this", "conversation_id": str(conversation_id)},
        files={"files": ("notes.txt", b"not a pdf", "text/plain")},
    ).status_code == 415
    assert client.post(
        "/api/ai/chat/pdf",
        headers=headers,
        data={"message": "Read this", "conversation_id": str(conversation_id)},
        files={"files": ("empty.pdf", b"", "application/pdf")},
    ).status_code == 400

    monkeypatch.setattr("app.api.routes_ai.settings.max_upload_size_mb", 0)
    assert client.post(
        "/api/ai/chat/pdf",
        headers=headers,
        data={"message": "Read this", "conversation_id": str(conversation_id)},
        files={"files": ("large.pdf", b"%PDF-1.4\ncontent", "application/pdf")},
    ).status_code == 413


def test_pdf_upload_rejects_missing_auth_and_missing_conversation(client, db_session):
    headers = auth_headers(client, db_session, "pdf-conversation@example.com")

    assert client.post(
        "/api/ai/chat/pdf",
        data={"message": "Read this"},
        files={"files": ("statement.pdf", b"%PDF-1.4\ncontent", "application/pdf")},
    ).status_code == 401
    assert client.post(
        "/api/ai/chat/pdf",
        headers=headers,
        data={"message": "Read this", "conversation_id": "99999"},
        files={"files": ("statement.pdf", b"%PDF-1.4\ncontent", "application/pdf")},
    ).status_code == 404
