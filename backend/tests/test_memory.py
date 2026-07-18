from app.ai.dependencies import get_ai_advisor_service
from app.main import app


class SuccessfulTestAdvisorService:
    model = "test-model"

    async def reply(
        self,
        message: str,
        system_instruction: str | None = None,
    ) -> str:
        del system_instruction
        return f"Educational response for: {message}"


class CapturingTestAdvisorService:
    model = "test-model"

    def __init__(self) -> None:
        self.messages: list[str] = []

    async def reply(
        self,
        message: str,
        system_instruction: str | None = None,
    ) -> str:
        del system_instruction
        self.messages.append(message)
        return "Educational response."


def create_authorization_headers(client) -> dict[str, str]:
    client.post(
        "/api/auth/register",
        json={
            "email": "memory@example.com",
            "password": "Password123",
        },
    )

    login_response = client.post(
        "/api/auth/login",
        json={
            "email": "memory@example.com",
            "password": "Password123",
        },
    )

    access_token = login_response.json()[
        "access_token"
    ]

    return {
        "Authorization": f"Bearer {access_token}",
    }


def test_memory_crud_and_export(client):
    headers = create_authorization_headers(client)

    create_response = client.post(
        "/api/memory",
        headers=headers,
        json={
            "fact": " I prefer low-risk investment explanations. ",
            "category": "preference",
        },
    )

    assert create_response.status_code == 201
    memory = create_response.json()
    assert memory["fact"] == "I prefer low-risk investment explanations."
    assert memory["category"] == "preference"
    assert memory["source"] == "manual"

    list_response = client.get("/api/memory", headers=headers)
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1

    update_response = client.put(
        f"/api/memory/{memory['id']}",
        headers=headers,
        json={
            "fact": "I prefer conservative budgeting advice.",
            "category": "preference",
        },
    )

    assert update_response.status_code == 200
    assert update_response.json()["fact"] == (
        "I prefer conservative budgeting advice."
    )

    export_response = client.get("/api/memory/export", headers=headers)
    assert export_response.status_code == 200
    assert export_response.json()["memories"][0]["fact"] == (
        "I prefer conservative budgeting advice."
    )

    delete_response = client.delete(
        f"/api/memory/{memory['id']}",
        headers=headers,
    )

    assert delete_response.status_code == 204
    assert client.get("/api/memory", headers=headers).json() == []


def test_ai_recalls_memory_across_conversations(client):
    headers = create_authorization_headers(client)
    service = CapturingTestAdvisorService()
    app.dependency_overrides[
        get_ai_advisor_service
    ] = lambda: service

    try:
        first_conversation_id = client.post(
            "/api/chat/conversations",
            headers=headers,
            json={},
        ).json()["conversation_id"]
        first_response = client.post(
            "/api/ai/chat",
            headers=headers,
            json={
                "message": "I have a $500 monthly car loan.",
                "conversation_id": first_conversation_id,
            },
        )

        second_conversation_id = client.post(
            "/api/chat/conversations",
            headers=headers,
            json={},
        ).json()["conversation_id"]
        second_response = client.post(
            "/api/ai/chat",
            headers=headers,
            json={
                "message": "Can I afford to save $200 this month?",
                "conversation_id": second_conversation_id,
            },
        )
    finally:
        app.dependency_overrides.pop(
            get_ai_advisor_service,
            None,
        )

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert len(service.messages) == 2
    assert "Long-term user memory" in service.messages[1]
    assert "I have a $500 monthly car loan" in service.messages[1]

    memories = client.get("/api/memory", headers=headers).json()
    assert len(memories) == 1
    car_loan_memory = next(
        item for item in memories if "car loan" in item["fact"]
    )
    assert car_loan_memory["last_used_at"] is not None
