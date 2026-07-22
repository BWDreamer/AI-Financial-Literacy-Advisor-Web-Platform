from datetime import date, timedelta

from app.ai.dependencies import get_ai_advisor_service
from app.main import app
from tests.helpers import register_verified_user


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

    async def reply(
        self,
        message: str,
        system_instruction: str | None = None,
    ) -> str:
        del system_instruction
        self.messages.append(message)
        return "Captured educational response."


def complete_chat_goal(
    *,
    title: str,
    target_amount: int,
    priority: str,
    deadline_days: int = 365,
) -> dict:
    return {
        "category": "general_saving",
        "goal_title": title,
        "target_amount": target_amount,
        "deadline": (date.today() + timedelta(days=deadline_days)).isoformat(),
        "current_amount": 0,
        "monthly_contribution": 500,
        "priority": priority,
    }


def goal_state(
    recommendation_status: str = "needs_recommendation",
    goals: list[dict] | None = None,
) -> dict:
    planned_goals = goals or [
        complete_chat_goal(
            title="Reliable used car",
            target_amount=15000,
            priority="Medium",
            deadline_days=730,
        )
    ]
    return {
        "goal_count": len(planned_goals),
        "goals": planned_goals,
        "recommendation_status": recommendation_status,
    }


class GoalPlanningAdvisorService(CapturingAdvisorService):
    def __init__(self, planned_state: dict | None = None) -> None:
        super().__init__()
        self.extraction_messages: list[str] = []
        self.planned_state = planned_state or goal_state()

    async def reply_json(
        self,
        message: str,
        response_schema: dict,
    ) -> dict:
        del response_schema
        if message.startswith("Extract and complete the user's goal-planning state"):
            self.extraction_messages.append(message)
            return self.planned_state
        return await super().reply_json(message, {})


class SequencedGoalPlanningAdvisorService(CapturingAdvisorService):
    def __init__(self, planned_states: list[dict]) -> None:
        super().__init__()
        self.extraction_messages: list[str] = []
        self.planned_states = planned_states

    async def reply_json(
        self,
        message: str,
        response_schema: dict,
    ) -> dict:
        del response_schema
        if message.startswith("Extract and complete the user's goal-planning state"):
            extraction_index = len(self.extraction_messages)
            self.extraction_messages.append(message)
            return self.planned_states[
                min(extraction_index, len(self.planned_states) - 1)
            ]
        return await super().reply_json(message, {})


def authorization_headers(client, email: str) -> dict[str, str]:
    register_verified_user(
        client,
        {"email": email, "password": "Password123"},
    )
    response = client.post(
        "/api/auth/login",
        json={"email": email, "password": "Password123"},
    )
    return {
        "Authorization": f"Bearer {response.json()['access_token']}"
    }


def add_goal_planning_cash_flow(client, headers: dict[str, str]) -> None:
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
            "amount": 4100,
            "frequency": "monthly",
            "start_date": today,
        },
    ]:
        response = client.post(
            "/api/financials/recurring-cash-flows",
            headers=headers,
            json=payload,
        )
        assert response.status_code == 201


def create_conversation(client, headers: dict[str, str]) -> int:
    return client.post(
        "/api/chat/conversations",
        headers=headers,
        json={},
    ).json()["conversation_id"]


def test_goal_recommendation_packages_preference_profile_and_finances(client):
    headers = authorization_headers(client, "context@example.com")
    for memory in [
        {
            "category": "preference",
            "fact": "User prefers concise, balanced, practical plans.",
        },
        {
            "category": "profile",
            "fact": "User is new to financial planning.",
        },
    ]:
        response = client.post("/api/memory", headers=headers, json=memory)
        assert response.status_code == 201
    add_goal_planning_cash_flow(client, headers)
    conversation_id = create_conversation(client, headers)
    service = GoalPlanningAdvisorService()
    app.dependency_overrides[get_ai_advisor_service] = lambda: service
    try:
        response = client.post(
            "/api/ai/chat",
            headers=headers,
            json={
                "message": "I want to save for a reliable used car.",
                "conversation_id": conversation_id,
            },
        )
    finally:
        app.dependency_overrides.pop(get_ai_advisor_service, None)

    assert response.status_code == 200
    assert len(service.extraction_messages) == 1
    extraction_prompt = service.extraction_messages[0]
    final_prompt = service.messages[0]
    for expected_memory in [
        "preference: User prefers concise, balanced, practical plans",
        "profile: User is new to financial planning",
    ]:
        assert expected_memory in extraction_prompt
        assert expected_memory in final_prompt
    assert "Ongoing monthly surplus" in extraction_prompt
    assert "$900.00" in extraction_prompt
    assert "Stage: complete recommendation awaiting approval" in final_prompt
    assert "Target amount: $15,000.00" in final_prompt
    assert "Does this overall plan work for you?" in final_prompt
    assert "How much do you want to save?" not in final_prompt
    assert "How much have you already saved?" not in final_prompt


def test_goal_category_ui_metadata_enters_the_planning_prompt(client):
    headers = authorization_headers(client, "category-selection@example.com")
    add_goal_planning_cash_flow(client, headers)
    conversation_id = create_conversation(client, headers)
    category_prompt = client.post(
        f"/api/chat/conversations/{conversation_id}/messages",
        headers=headers,
        json={
            "role": "assistant",
            "content": (
                "What Budget / Cash Flow goal would you like to set?\n\n"
                "[Financial goal planning mode: category=budget]"
            ),
        },
    )
    assert category_prompt.status_code == 201
    service = GoalPlanningAdvisorService()
    app.dependency_overrides[get_ai_advisor_service] = lambda: service
    try:
        response = client.post(
            "/api/ai/chat",
            headers=headers,
            json={
                "message": "Make my monthly finances feel less stressful.",
                "conversation_id": conversation_id,
            },
        )
    finally:
        app.dependency_overrides.pop(get_ai_advisor_service, None)

    assert response.status_code == 200
    assert len(service.extraction_messages) == 1
    assert "Financial goal planning mode: category=budget" in (
        service.extraction_messages[0]
    )


def test_goal_recommendation_is_not_blocked_without_financial_records(client):
    headers = authorization_headers(client, "missing-context@example.com")
    service = GoalPlanningAdvisorService()
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
    prompt = service.messages[0]
    assert "Financial records: none" in prompt
    assert "Stage: complete recommendation awaiting approval" in prompt
    assert "illustrative requirement" in prompt
    assert "an upload is not a prerequisite" in prompt


def test_user_acceptance_completes_the_goal_plan(client):
    headers = authorization_headers(client, "accepted@example.com")
    add_goal_planning_cash_flow(client, headers)
    conversation_id = create_conversation(client, headers)
    service = SequencedGoalPlanningAdvisorService(
        [goal_state(), goal_state("accepted")]
    )
    app.dependency_overrides[get_ai_advisor_service] = lambda: service
    try:
        first_response = client.post(
            "/api/ai/chat",
            headers=headers,
            json={
                "message": "I want to save for a reliable used car.",
                "conversation_id": conversation_id,
            },
        )
        second_response = client.post(
            "/api/ai/chat",
            headers=headers,
            json={
                "message": "Yes, that overall plan works for me.",
                "conversation_id": conversation_id,
            },
        )
    finally:
        app.dependency_overrides.pop(get_ai_advisor_service, None)

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    final_prompt = service.messages[1]
    assert "Earlier messages in this same conversation" in final_prompt
    assert "Stage: confirmed goal plan" in final_prompt
    assert "planning is complete" in final_prompt
    assert "Does this overall plan work for you?" not in final_prompt
    assert "Do not ask another question" in final_prompt


def test_user_rejection_only_triggers_a_macro_question(client):
    headers = authorization_headers(client, "rejected@example.com")
    add_goal_planning_cash_flow(client, headers)
    conversation_id = create_conversation(client, headers)
    service = SequencedGoalPlanningAdvisorService(
        [goal_state(), goal_state("rejected")]
    )
    app.dependency_overrides[get_ai_advisor_service] = lambda: service
    try:
        client.post(
            "/api/ai/chat",
            headers=headers,
            json={
                "message": "I want to save for a reliable used car.",
                "conversation_id": conversation_id,
            },
        )
        response = client.post(
            "/api/ai/chat",
            headers=headers,
            json={
                "message": "No, I do not agree with that plan.",
                "conversation_id": conversation_id,
            },
        )
    finally:
        app.dependency_overrides.pop(get_ai_advisor_service, None)

    assert response.status_code == 200
    prompt = service.messages[1]
    assert "Stage: recommendation rejected; collect macro direction" in prompt
    assert "ask exactly one concise macro-level question" in prompt
    assert "faster progress, more monthly flexibility, lower pressure" in prompt
    assert "Target amount: $" not in prompt
    assert "Recommended ongoing monthly allocation:" not in prompt


def test_macro_answer_produces_a_revised_complete_recommendation(client):
    headers = authorization_headers(client, "revision@example.com")
    add_goal_planning_cash_flow(client, headers)
    conversation_id = create_conversation(client, headers)
    revised_goal = complete_chat_goal(
        title="Reliable used car",
        target_amount=12000,
        priority="Low",
        deadline_days=1095,
    )
    service = SequencedGoalPlanningAdvisorService(
        [
            goal_state(),
            goal_state("rejected"),
            goal_state("needs_recommendation", [revised_goal]),
        ]
    )
    app.dependency_overrides[get_ai_advisor_service] = lambda: service
    try:
        for message in [
            "I want to save for a reliable used car.",
            "No, I do not agree with that plan.",
            "I want lower pressure and more monthly flexibility.",
        ]:
            response = client.post(
                "/api/ai/chat",
                headers=headers,
                json={"message": message, "conversation_id": conversation_id},
            )
    finally:
        app.dependency_overrides.pop(get_ai_advisor_service, None)

    assert response.status_code == 200
    prompt = service.messages[2]
    assert "Stage: complete recommendation awaiting approval" in prompt
    assert "Target amount: $12,000.00" in prompt
    assert "Priority: Low" in prompt
    assert "Does this overall plan work for you?" in prompt


def test_goal_count_correction_preserves_all_goals_in_recommendation(client):
    headers = authorization_headers(client, "four-goals@example.com")
    add_goal_planning_cash_flow(client, headers)
    goals = [
        complete_chat_goal(
            title=title,
            target_amount=amount,
            priority=priority,
            deadline_days=deadline_days,
        )
        for title, amount, priority, deadline_days in [
            ("Computer", 2000, "High", 60),
            ("RTX 5090", 4000, "Medium", 90),
            ("Mercedes", 80000, "Medium", 3650),
            ("House", 500000, "Low", 7300),
        ]
    ]
    incomplete_state = {
        "goal_count": 4,
        "goals": [goals[0]],
        "recommendation_status": "needs_recommendation",
    }
    service = SequencedGoalPlanningAdvisorService(
        [incomplete_state, goal_state("needs_recommendation", goals)]
    )
    app.dependency_overrides[get_ai_advisor_service] = lambda: service
    try:
        response = client.post(
            "/api/ai/chat",
            headers=headers,
            json={
                "message": (
                    "I want to buy a computer, an RTX 5090, a Mercedes, and a house."
                )
            },
        )
    finally:
        app.dependency_overrides.pop(get_ai_advisor_service, None)

    assert response.status_code == 200
    assert len(service.extraction_messages) == 2
    assert "Correction required" in service.extraction_messages[1]
    prompt = service.messages[0]
    assert "Recognized goals to cover in the final response: 4" in prompt
    assert prompt.count("Recommended ongoing monthly allocation:") == 4
    for title in ["Computer", "RTX 5090", "Mercedes", "House"]:
        assert f"Goal: {title}" in prompt
