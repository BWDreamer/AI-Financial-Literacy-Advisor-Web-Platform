from app.ai.dependencies import get_ai_advisor_service
from app.ai.exceptions import LLMRateLimitError
from app.main import app
from app.services.memory_service import extract_memories_from_message
from tests.helpers import register_verified_user


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


class SequencedTestAdvisorService:
    model = "test-model"

    def __init__(self, responses: list[str]) -> None:
        self.responses = responses
        self.index = 0

    async def reply(
        self,
        message: str,
        system_instruction: str | None = None,
    ) -> str:
        del message, system_instruction
        response = self.responses[min(self.index, len(self.responses) - 1)]
        self.index += 1
        return response


class RecommendationMemoryAdvisorService:
    model = "test-model"

    async def reply(
        self,
        message: str,
        system_instruction: str | None = None,
    ) -> str:
        del message, system_instruction
        return (
            "I recommend saving $1,000 per month for your emergency fund."
        )

    async def reply_json(
        self,
        message: str,
        response_schema: dict,
    ) -> dict:
        del response_schema
        if message.startswith(
            "Extract durable long-term memories from one finance-advisor turn."
        ):
            return {
                "memories": [
                    {
                        "fact": (
                            "My recommended monthly emergency fund "
                            "contribution is $1,000."
                        ),
                        "category": "goal",
                        "replaces_memory_id": None,
                    }
                ]
            }
        return {
            "intent": "out_of_scope",
            "rule_year": None,
            "taxable_income": None,
            "confidence": 0.0,
        }


class MemoryExtractionFailureAdvisorService:
    model = "test-model"

    async def reply(
        self,
        message: str,
        system_instruction: str | None = None,
    ) -> str:
        del message, system_instruction
        return "Thanks, I have noted your updated car loan."

    async def reply_json(
        self,
        message: str,
        response_schema: dict,
    ) -> dict:
        del response_schema
        if message.startswith(
            "Extract durable long-term memories from one finance-advisor turn."
        ):
            raise LLMRateLimitError("Memory extraction was rate limited.")
        return {
            "intent": "out_of_scope",
            "rule_year": None,
            "taxable_income": None,
            "confidence": 0.0,
        }


class ForeignReplacementAdvisorService:
    model = "test-model"

    def __init__(self, foreign_memory_id: int) -> None:
        self.foreign_memory_id = foreign_memory_id

    async def reply(
        self,
        message: str,
        system_instruction: str | None = None,
    ) -> str:
        del message, system_instruction
        return "Confirmed: your car loan balance is $2,000."

    async def reply_json(
        self,
        message: str,
        response_schema: dict,
    ) -> dict:
        del response_schema
        if message.startswith(
            "Extract durable long-term memories from one finance-advisor turn."
        ):
            return {
                "memories": [
                    {
                        "fact": "My car loan balance is $2,000.",
                        "category": "debt",
                        "replaces_memory_id": self.foreign_memory_id,
                    }
                ]
            }
        return {
            "intent": "out_of_scope",
            "rule_year": None,
            "taxable_income": None,
            "confidence": 0.0,
        }


def create_authorization_headers(
    client,
    email: str = "memory@example.com",
) -> dict[str, str]:
    register_verified_user(
        client,
        {
            "email": email,
            "password": "Password123",
        },
    )

    login_response = client.post(
        "/api/auth/login",
        json={
            "email": email,
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

    detail_response = client.get(
        f"/api/memory/{memory['id']}",
        headers=headers,
    )
    assert detail_response.status_code == 200
    assert detail_response.json()["id"] == memory["id"]

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
    assert client.get(
        f"/api/memory/{memory['id']}",
        headers=headers,
    ).status_code == 404


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
    assert first_response.json()["memory_updated"] is True
    assert first_response.json()["memory_update_count"] == 1
    assert second_response.json()["memory_updated"] is False
    assert second_response.json()["memory_update_count"] == 0
    assert len(service.messages) == 2
    assert "Long-term user memory" in service.messages[1]
    assert "I have a $500 monthly car loan" in service.messages[1]

    memories = client.get("/api/memory", headers=headers).json()
    assert len(memories) == 1
    car_loan_memory = next(
        item for item in memories if "car loan" in item["fact"]
    )
    assert car_loan_memory["last_used_at"] is not None


def test_repeated_fact_does_not_report_a_memory_update(client):
    headers = create_authorization_headers(client)
    service = CapturingTestAdvisorService()
    app.dependency_overrides[get_ai_advisor_service] = lambda: service

    try:
        first_response = client.post(
            "/api/ai/chat",
            headers=headers,
            json={"message": "I have a $500 monthly car loan."},
        )
        repeated_response = client.post(
            "/api/ai/chat",
            headers=headers,
            json={"message": "I have a $500 monthly car loan."},
        )
    finally:
        app.dependency_overrides.pop(get_ai_advisor_service, None)

    assert first_response.status_code == 200
    assert first_response.json()["memory_updated"] is True
    assert first_response.json()["memory_update_count"] == 1
    assert repeated_response.status_code == 200
    assert repeated_response.json()["memory_updated"] is False
    assert repeated_response.json()["memory_update_count"] == 0
    assert len(client.get("/api/memory", headers=headers).json()) == 1


def test_memory_extraction_preserves_decimals_and_declarative_question_prefix():
    extracted = extract_memories_from_message(
        "My monthly income is $3,000.50, can I afford higher rent?"
    )

    assert len(extracted) == 1
    assert extracted[0].fact == "My monthly income is $3,000.50"
    assert extracted[0].category == "income"


def test_short_amount_answer_uses_previous_assistant_question(client):
    headers = create_authorization_headers(client)
    service = SequencedTestAdvisorService(
        [
            "What is your current car loan balance?",
            "Thanks, I have recorded that amount.",
        ]
    )
    app.dependency_overrides[get_ai_advisor_service] = lambda: service

    try:
        conversation_id = client.post(
            "/api/chat/conversations",
            headers=headers,
            json={},
        ).json()["conversation_id"]
        first_response = client.post(
            "/api/ai/chat",
            headers=headers,
            json={
                "message": "Please record my current loan.",
                "conversation_id": conversation_id,
            },
        )
        second_response = client.post(
            "/api/ai/chat",
            headers=headers,
            json={
                "message": "$1,000",
                "conversation_id": conversation_id,
            },
        )
    finally:
        app.dependency_overrides.pop(get_ai_advisor_service, None)

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    memories = client.get("/api/memory", headers=headers).json()
    assert len(memories) == 1
    assert memories[0]["fact"] == "My car loan balance is $1,000."
    assert memories[0]["category"] == "debt"


def test_assistant_recommendation_is_saved_as_memory(client):
    headers = create_authorization_headers(client)
    service = RecommendationMemoryAdvisorService()
    app.dependency_overrides[get_ai_advisor_service] = lambda: service

    try:
        response = client.post(
            "/api/ai/chat",
            headers=headers,
            json={
                "message": "What should I contribute each month?",
            },
        )
    finally:
        app.dependency_overrides.pop(get_ai_advisor_service, None)

    assert response.status_code == 200
    memories = client.get("/api/memory", headers=headers).json()
    assert len(memories) == 1
    assert memories[0]["fact"] == (
        "My recommended monthly emergency fund contribution is $1,000."
    )
    assert memories[0]["category"] == "goal"


def test_assistant_recommendation_has_rule_based_fallback(client):
    headers = create_authorization_headers(client)
    service = SequencedTestAdvisorService(
        ["I recommend saving $750 per month for your emergency fund."]
    )
    app.dependency_overrides[get_ai_advisor_service] = lambda: service

    try:
        response = client.post(
            "/api/ai/chat",
            headers=headers,
            json={"message": "What monthly amount would you recommend?"},
        )
    finally:
        app.dependency_overrides.pop(get_ai_advisor_service, None)

    assert response.status_code == 200
    memories = client.get("/api/memory", headers=headers).json()
    assert len(memories) == 1
    assert memories[0]["fact"] == (
        "AI recommendation: I recommend saving $750 per month for your "
        "emergency fund"
    )
    assert memories[0]["category"] == "goal"


def test_changed_car_loan_replaces_previous_memory(client):
    headers = create_authorization_headers(client)
    service = SequencedTestAdvisorService(["Thanks."])
    app.dependency_overrides[get_ai_advisor_service] = lambda: service

    try:
        conversation_id = client.post(
            "/api/chat/conversations",
            headers=headers,
            json={},
        ).json()["conversation_id"]
        for message in [
            "I have a $3,000 car loan.",
            "My car loan increased to $5,000.",
            "It decreased to $2,000.",
        ]:
            response = client.post(
                "/api/ai/chat",
                headers=headers,
                json={
                    "message": message,
                    "conversation_id": conversation_id,
                },
            )
            assert response.status_code == 200
    finally:
        app.dependency_overrides.pop(get_ai_advisor_service, None)

    memories = client.get("/api/memory", headers=headers).json()
    assert len(memories) == 1
    assert memories[0]["fact"] == "My car loan balance is $2,000."
    assert memories[0]["source"] == "chat"


def test_paid_off_debt_and_changed_preference_replace_old_values(client):
    headers = create_authorization_headers(client)
    service = SequencedTestAdvisorService(["Thanks."])
    app.dependency_overrides[get_ai_advisor_service] = lambda: service

    try:
        for message in [
            "I have a $3,000 car loan.",
            "I have paid off my car loan.",
            "I prefer conservative, low-risk advice.",
            "I now prefer aggressive, high-risk advice.",
        ]:
            response = client.post(
                "/api/ai/chat",
                headers=headers,
                json={"message": message},
            )
            assert response.status_code == 200
    finally:
        app.dependency_overrides.pop(get_ai_advisor_service, None)

    memories = client.get("/api/memory", headers=headers).json()
    assert len(memories) == 2
    facts = {memory["category"]: memory["fact"] for memory in memories}
    assert facts["debt"] == "I have paid off my car loan"
    assert facts["preference"] == (
        "I now prefer aggressive, high-risk advice"
    )


def test_balance_and_interest_rate_remain_separate_memories(client):
    headers = create_authorization_headers(client)
    service = SequencedTestAdvisorService(["Thanks."])
    app.dependency_overrides[get_ai_advisor_service] = lambda: service

    try:
        for message in [
            "My car loan balance is $3,000.",
            "My car loan interest rate is 7%.",
            "My car loan balance increased to $4,000.",
            "My car loan interest rate increased to 8%.",
        ]:
            response = client.post(
                "/api/ai/chat",
                headers=headers,
                json={"message": message},
            )
            assert response.status_code == 200
    finally:
        app.dependency_overrides.pop(get_ai_advisor_service, None)

    memories = client.get("/api/memory", headers=headers).json()
    assert len(memories) == 2
    facts = {memory["fact"] for memory in memories}
    assert "My car loan balance is $4,000." in facts
    assert "My car loan interest rate is 8%." in facts


def test_chat_update_removes_existing_same_topic_duplicates(client):
    headers = create_authorization_headers(client)
    first = client.post(
        "/api/memory",
        headers=headers,
        json={
            "fact": "My car loan balance is $3,000.",
            "category": "debt",
        },
    ).json()
    second = client.post(
        "/api/memory",
        headers=headers,
        json={
            "fact": "My car loan balance is $5,000.",
            "category": "debt",
        },
    ).json()
    assert first["id"] != second["id"]

    service = SequencedTestAdvisorService(["Thanks."])
    app.dependency_overrides[get_ai_advisor_service] = lambda: service
    try:
        response = client.post(
            "/api/ai/chat",
            headers=headers,
            json={"message": "My car loan decreased to $2,000."},
        )
    finally:
        app.dependency_overrides.pop(get_ai_advisor_service, None)

    assert response.status_code == 200
    memories = client.get("/api/memory", headers=headers).json()
    assert len(memories) == 1
    assert memories[0]["fact"] == "My car loan balance is $2,000."


def test_conflicting_existing_memories_are_deduplicated_for_ai_context(client):
    headers = create_authorization_headers(client)
    for amount in ("$3,000", "$5,000"):
        response = client.post(
            "/api/memory",
            headers=headers,
            json={
                "fact": f"My car loan balance is {amount}.",
                "category": "debt",
            },
        )
        assert response.status_code == 201

    service = CapturingTestAdvisorService()
    app.dependency_overrides[get_ai_advisor_service] = lambda: service
    try:
        response = client.post(
            "/api/ai/chat",
            headers=headers,
            json={"message": "What is my car loan balance?"},
        )
    finally:
        app.dependency_overrides.pop(get_ai_advisor_service, None)

    assert response.status_code == 200
    assert len(service.messages) == 1
    assert "My car loan balance is $5,000." in service.messages[0]
    assert "My car loan balance is $3,000." not in service.messages[0]


def test_memory_extraction_failure_does_not_fail_chat_or_fallback(client):
    headers = create_authorization_headers(client)
    service = MemoryExtractionFailureAdvisorService()
    app.dependency_overrides[get_ai_advisor_service] = lambda: service

    try:
        response = client.post(
            "/api/ai/chat",
            headers=headers,
            json={"message": "My car loan is now $4,000."},
        )
    finally:
        app.dependency_overrides.pop(get_ai_advisor_service, None)

    assert response.status_code == 200
    memories = client.get("/api/memory", headers=headers).json()
    assert len(memories) == 1
    assert memories[0]["fact"] == "My car loan balance is $4,000."


def test_ai_cannot_replace_another_users_memory(client):
    first_headers = create_authorization_headers(
        client,
        email="first-memory@example.com",
    )
    first_memory = client.post(
        "/api/memory",
        headers=first_headers,
        json={
            "fact": "My car loan balance is $9,000.",
            "category": "debt",
        },
    ).json()
    second_headers = create_authorization_headers(
        client,
        email="second-memory@example.com",
    )

    service = ForeignReplacementAdvisorService(first_memory["id"])
    app.dependency_overrides[get_ai_advisor_service] = lambda: service
    try:
        response = client.post(
            "/api/ai/chat",
            headers=second_headers,
            json={"message": "Please confirm the corrected amount."},
        )
    finally:
        app.dependency_overrides.pop(get_ai_advisor_service, None)

    assert response.status_code == 200
    first_memories = client.get(
        "/api/memory",
        headers=first_headers,
    ).json()
    second_memories = client.get(
        "/api/memory",
        headers=second_headers,
    ).json()
    assert first_memories[0]["fact"] == "My car loan balance is $9,000."
    assert second_memories[0]["fact"] == "My car loan balance is $2,000."
    assert first_memories[0]["id"] != second_memories[0]["id"]
