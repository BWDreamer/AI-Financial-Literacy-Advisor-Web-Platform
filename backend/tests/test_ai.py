from app.ai.dependencies import get_ai_advisor_service
from app.ai.exceptions import LLMConfigurationError
from app.ai.prompts import FINANCIAL_ADVISOR_INSTRUCTIONS
from app.main import app


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


def test_financial_advisor_prompt_requires_readable_lists():
    normalized_prompt = " ".join(
        FINANCIAL_ADVISOR_INSTRUCTIONS.split()
    )

    assert "Format responses for readability" in normalized_prompt
    assert "put each list item on its own separate line" in (
        normalized_prompt
    )
    assert "Do not compress multiple list items" in (
        normalized_prompt
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
