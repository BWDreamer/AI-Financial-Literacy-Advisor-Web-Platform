from datetime import date

from app.ai.dependencies import get_ai_advisor_service
from app.main import app


class CapturingAdvisorService:
    model = "test-model"

    def __init__(self) -> None:
        self.messages: list[str] = []

    async def reply_json(
        self,
        message: str,
        response_schema: dict,
    ) -> dict:
        del message, response_schema
        return {
            "intent": "out_of_scope",
            "rule_year": None,
            "taxable_income": None,
            "confidence": 0.0,
        }

    async def reply(self, message: str) -> str:
        self.messages.append(message)
        return "Captured educational response."


def authorization_headers(client, email: str) -> dict[str, str]:
    client.post(
        "/api/auth/register",
        json={"email": email, "password": "Password123"},
    )
    response = client.post(
        "/api/auth/login",
        json={"email": email, "password": "Password123"},
    )
    return {
        "Authorization": f"Bearer {response.json()['access_token']}"
    }


def test_chat_uses_history_profile_and_separated_financial_context(client):
    headers = authorization_headers(client, "context@example.com")
    client.post(
        "/api/memory",
        headers=headers,
        json={
            "category": "preference",
            "fact": "User prefers concise and practical guidance.",
        },
    )
    today = date.today().isoformat()
    for payload in [
        {
            "flow_type": "income",
            "name": "Salary",
            "amount": 5000,
            "frequency": "monthly",
            "start_date": today,
        },
        {
            "flow_type": "expense",
            "name": "Living costs",
            "amount": 3200,
            "frequency": "monthly",
            "start_date": today,
        },
    ]:
        client.post(
            "/api/financials/recurring-cash-flows",
            headers=headers,
            json=payload,
        )
    for payload in [
        {
            "flow_type": "income",
            "name": "Bonus",
            "amount": 1000,
            "date": today,
        },
        {
            "flow_type": "expense",
            "name": "Car repair",
            "amount": 300,
            "date": today,
        },
    ]:
        client.post(
            "/api/financials/cash-flows",
            headers=headers,
            json=payload,
        )

    conversation_id = client.post(
        "/api/chat/conversations",
        headers=headers,
        json={},
    ).json()["conversation_id"]
    service = CapturingAdvisorService()
    app.dependency_overrides[get_ai_advisor_service] = lambda: service
    try:
        first_response = client.post(
            "/api/ai/chat",
            headers=headers,
            json={
                "message": "I want to build an emergency fund.",
                "conversation_id": conversation_id,
            },
        )
        second_response = client.post(
            "/api/ai/chat",
            headers=headers,
            json={
                "message": "I would like it to cover three months.",
                "conversation_id": conversation_id,
            },
        )
    finally:
        app.dependency_overrides.pop(get_ai_advisor_service, None)

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert len(service.messages) == 2
    second_prompt = service.messages[1]
    assert "User prefers concise and practical guidance" in second_prompt
    assert "Earlier messages in this same conversation" in second_prompt
    assert "User: I want to build an emergency fund." in second_prompt
    assert "Ongoing monthly surplus" in second_prompt
    assert "$1,800.00" in second_prompt
    assert "One-off surplus" in second_prompt
    assert "$700.00" in second_prompt


def test_chat_context_requires_pdf_when_financial_records_are_missing(client):
    headers = authorization_headers(client, "missing-context@example.com")
    service = CapturingAdvisorService()
    app.dependency_overrides[get_ai_advisor_service] = lambda: service
    try:
        response = client.post(
            "/api/ai/chat",
            headers=headers,
            json={"message": "I want to save for a home deposit."},
        )
    finally:
        app.dependency_overrides.pop(get_ai_advisor_service, None)

    assert response.status_code == 200
    assert len(service.messages) == 1
    assert "Financial records: none" in service.messages[0]
    assert "upload a bank statement or transaction PDF" in service.messages[0]
    assert "+ button in AI Chat" in service.messages[0]
