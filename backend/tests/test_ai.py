from app.ai.dependencies import get_ai_advisor_service
from app.ai.exceptions import LLMConfigurationError
from app.main import app
from app.models.financial_rule import FinancialRule


class SuccessfulTestAdvisorService:
    model = "test-model"

    async def reply(
        self,
        message: str,
    ) -> str:
        return f"Educational response for: {message}"


class UnconfiguredTestAdvisorService:
    model = "test-model"

    async def reply(
        self,
        message: str,
    ) -> str:
        del message

        raise LLMConfigurationError(
            "Test provider is not configured."
        )


def create_authorization_headers(client) -> dict[str, str]:
    client.post(
        "/api/auth/register",
        json={
            "email": "advisor@example.com",
            "password": "Password123",
        },
    )

    login_response = client.post(
        "/api/auth/login",
        json={
            "email": "advisor@example.com",
            "password": "Password123",
        },
    )

    access_token = login_response.json()[
        "access_token"
    ]

    return {
        "Authorization": f"Bearer {access_token}",
    }


def test_chat_requires_authentication(client):
    response = client.post(
        "/api/ai/chat",
        json={
            "message": "What is compound interest?",
        },
    )

    assert response.status_code == 401


def test_chat_returns_advisor_response(client):
    app.dependency_overrides[
        get_ai_advisor_service
    ] = lambda: SuccessfulTestAdvisorService()

    try:
        response = client.post(
            "/api/ai/chat",
            headers=create_authorization_headers(
                client
            ),
            json={
                "message": "  What is compound interest?  ",
            },
        )
    finally:
        app.dependency_overrides.pop(
            get_ai_advisor_service,
            None,
        )

    assert response.status_code == 200
    assert response.json() == {
        "answer": (
            "Educational response for: "
            "What is compound interest?"
        ),
        "model": "test-model",
    }


def test_chat_rejects_blank_message(client):
    response = client.post(
        "/api/ai/chat",
        headers=create_authorization_headers(
            client
        ),
        json={
            "message": "   ",
        },
    )

    assert response.status_code == 422


def test_chat_reports_missing_api_configuration(client):
    app.dependency_overrides[
        get_ai_advisor_service
    ] = lambda: UnconfiguredTestAdvisorService()

    try:
        response = client.post(
            "/api/ai/chat",
            headers=create_authorization_headers(
                client
            ),
            json={
                "message": "What is compound interest?",
            },
        )
    finally:
        app.dependency_overrides.pop(
            get_ai_advisor_service,
            None,
        )

    assert response.status_code == 503
    assert response.json()["detail"] == (
        "The AI service is not configured. "
        "Set GEMINI_API_KEY on the backend."
    )


def test_chat_includes_selected_rule_context(client, db_session):
    rule = FinancialRule(
        region="Australia",
        category="tax",
        rule_year="2025-2026",
        rule_key="test_rule",
        rule_value="Verified test rule content.",
        source_name="Australian Taxation Office",
        source_url="https://www.ato.gov.au/",
    )
    db_session.add(rule)
    db_session.commit()

    service = SuccessfulTestAdvisorService()
    app.dependency_overrides[get_ai_advisor_service] = lambda: service
    try:
        response = client.post(
            "/api/ai/chat",
            headers=create_authorization_headers(client),
            json={"message": "Explain this rule", "rule_id": rule.id},
        )
    finally:
        app.dependency_overrides.pop(get_ai_advisor_service, None)

    assert response.status_code == 200
    answer = response.json()["answer"]
    assert "Verified test rule content." in answer
    assert "Australian Taxation Office" in answer


def test_chat_rejects_missing_selected_rule(client):
    app.dependency_overrides[
        get_ai_advisor_service
    ] = lambda: SuccessfulTestAdvisorService()
    try:
        response = client.post(
            "/api/ai/chat",
            headers=create_authorization_headers(client),
            json={"message": "Explain this rule", "rule_id": 99999},
        )
    finally:
        app.dependency_overrides.pop(get_ai_advisor_service, None)

    assert response.status_code == 404
