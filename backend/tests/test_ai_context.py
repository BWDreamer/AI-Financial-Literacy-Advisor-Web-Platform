from datetime import date, timedelta

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


class GoalPlanningAdvisorService(CapturingAdvisorService):
    def __init__(self, goal_state: dict | None = None) -> None:
        super().__init__()
        self.extraction_messages: list[str] = []
        self.goal_state = goal_state or {
            "goal_count": 1,
            "goals": [
                {
                    "category": "general_saving",
                    "answered_fields": ["goal_title"],
                    "goal_title": "a reliable used car",
                    "priority": None,
                }
            ],
            "finished_adding_goals": False,
        }

    async def reply_json(
        self,
        message: str,
        response_schema: dict,
    ) -> dict:
        del response_schema
        if message.startswith("Extract the user's goal-planning state"):
            self.extraction_messages.append(message)
            return self.goal_state
        return await super().reply_json(message, {})


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


def test_chat_uses_structured_goal_state_to_choose_the_next_question(client):
    headers = authorization_headers(client, "goal-sequence@example.com")
    client.post(
        "/api/memory",
        headers=headers,
        json={
            "category": "preference",
            "fact": "User prefers short, practical plans.",
        },
    )
    client.post(
        "/api/financials/recurring-cash-flows",
        headers=headers,
        json={
            "flow_type": "income",
            "name": "Salary",
            "amount": 5000,
            "frequency": "monthly",
            "start_date": date.today().isoformat(),
        },
    )
    conversation_id = client.post(
        "/api/chat/conversations",
        headers=headers,
        json={},
    ).json()["conversation_id"]
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
    assert len(service.messages) == 1
    prompt = service.messages[0]
    assert "User prefers short, practical plans" in prompt
    assert "Next MyGoals field: target_amount" in prompt
    assert "Use this exact question: How much do you want to save?" in prompt
    assert "Do not ask any additional question" in prompt


def complete_chat_goal(
    *,
    title: str,
    target_amount: int,
    priority: str,
    confirm_priority: bool = True,
    deadline_days: int = 365,
) -> dict:
    answered_fields = [
        "goal_title",
        "target_amount",
        "deadline",
        "current_amount",
        "monthly_contribution",
    ]
    if confirm_priority:
        answered_fields.append("priority")
    return {
        "category": "general_saving",
        "answered_fields": answered_fields,
        "goal_title": title,
        "target_amount": target_amount,
        "deadline": (date.today() + timedelta(days=deadline_days)).isoformat(),
        "current_amount": 0,
        "monthly_contribution": 500,
        "priority": priority,
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


def test_chat_does_not_accept_an_ai_selected_goal_priority(client):
    headers = authorization_headers(client, "priority-gate@example.com")
    add_goal_planning_cash_flow(client, headers)
    state = {
        "goal_count": 1,
        "goals": [
            complete_chat_goal(
                title="Car",
                target_amount=12000,
                priority="High",
                confirm_priority=False,
            )
        ],
        "finished_adding_goals": True,
    }
    service = GoalPlanningAdvisorService(state)
    app.dependency_overrides[get_ai_advisor_service] = lambda: service
    try:
        response = client.post(
            "/api/ai/chat",
            headers=headers,
            json={"message": "These are all my goals."},
        )
    finally:
        app.dependency_overrides.pop(get_ai_advisor_service, None)

    assert response.status_code == 200
    prompt = service.messages[0]
    assert "Next MyGoals field: priority" in prompt
    assert "which priority do you choose" in prompt
    assert "Do not choose, recommend, or imply any priority" in prompt
    assert "Stage: final negotiated allocation" not in prompt


def test_chat_allocates_surplus_across_all_user_prioritised_goals(client):
    headers = authorization_headers(client, "multi-goal@example.com")
    add_goal_planning_cash_flow(client, headers)
    state = {
        "goal_count": 2,
        "goals": [
            complete_chat_goal(
                title="Car",
                target_amount=12000,
                priority="High",
            ),
            complete_chat_goal(
                title="Travel",
                target_amount=6000,
                priority="Low",
            ),
        ],
        "finished_adding_goals": True,
    }
    service = GoalPlanningAdvisorService(state)
    app.dependency_overrides[get_ai_advisor_service] = lambda: service
    try:
        response = client.post(
            "/api/ai/chat",
            headers=headers,
            json={"message": "Those are all my goals."},
        )
    finally:
        app.dependency_overrides.pop(get_ai_advisor_service, None)

    assert response.status_code == 200
    prompt = service.messages[0]
    assert "Stage: final negotiated allocation" in prompt
    assert "Available ongoing monthly surplus for allocation: $900.00" in prompt
    assert "Goal: Car" in prompt
    assert "Priority: High" in prompt
    assert "Goal: Travel" in prompt
    assert "Priority: Low" in prompt
    assert "Recommended ongoing monthly allocation: $675.00" in prompt
    assert "Recommended ongoing monthly allocation: $225.00" in prompt


def test_chat_final_allocation_covers_all_four_recognized_goals(client):
    headers = authorization_headers(client, "four-goal-allocation@example.com")
    add_goal_planning_cash_flow(client, headers)
    state = {
        "goal_count": 4,
        "goals": [
            complete_chat_goal(
                title="Computer",
                target_amount=2000,
                priority="High",
                deadline_days=60,
            ),
            complete_chat_goal(
                title="RTX 5090",
                target_amount=4000,
                priority="Medium",
                deadline_days=90,
            ),
            complete_chat_goal(
                title="Mercedes",
                target_amount=80000,
                priority="Medium",
                deadline_days=3650,
            ),
            complete_chat_goal(
                title="House",
                target_amount=500000,
                priority="Low",
                deadline_days=7300,
            ),
        ],
        "finished_adding_goals": True,
    }
    service = GoalPlanningAdvisorService(state)
    app.dependency_overrides[get_ai_advisor_service] = lambda: service
    try:
        response = client.post(
            "/api/ai/chat",
            headers=headers,
            json={"message": "Those are all my goals."},
        )
    finally:
        app.dependency_overrides.pop(get_ai_advisor_service, None)

    assert response.status_code == 200
    prompt = service.messages[0]
    assert "Stage: final negotiated allocation" in prompt
    assert "Recognized goals to cover in the final response: 4" in prompt
    assert prompt.count("Recommended ongoing monthly allocation:") == 4
    for title in ["Computer", "RTX 5090", "Mercedes", "House"]:
        assert f"Goal: {title}" in prompt


class SequencedGoalPlanningAdvisorService(CapturingAdvisorService):
    def __init__(self, goal_states: list[dict]) -> None:
        super().__init__()
        self.extraction_messages: list[str] = []
        self.goal_states = goal_states

    async def reply_json(
        self,
        message: str,
        response_schema: dict,
    ) -> dict:
        del response_schema
        if message.startswith("Extract the user's goal-planning state"):
            extraction_index = len(self.extraction_messages)
            self.extraction_messages.append(message)
            return self.goal_states[min(extraction_index, len(self.goal_states) - 1)]
        return await super().reply_json(message, {})


def test_chat_rechecks_goal_count_and_questions_all_four_goals(client):
    headers = authorization_headers(client, "four-goals@example.com")
    add_goal_planning_cash_flow(client, headers)
    partial_goal = {
        "category": "general_saving",
        "answered_fields": ["goal_title", "target_amount", "deadline"],
        "priority": None,
    }
    complete_state = {
        "goal_count": 4,
        "goals": [
            {
                **partial_goal,
                "goal_title": "Computer",
                "target_amount": 2000,
                "deadline": "within two months",
            },
            {
                **partial_goal,
                "goal_title": "RTX 5090",
                "target_amount": 4000,
                "deadline": "within three months",
            },
            {
                **partial_goal,
                "goal_title": "Mercedes",
                "target_amount": 80000,
                "deadline": "within ten years",
            },
            {
                **partial_goal,
                "goal_title": "House",
                "target_amount": 500000,
                "deadline": "within twenty years",
            },
        ],
        "finished_adding_goals": True,
    }
    incomplete_state = {
        "goal_count": 4,
        "goals": [complete_state["goals"][0]],
        "finished_adding_goals": True,
    }
    service = SequencedGoalPlanningAdvisorService(
        [incomplete_state, complete_state]
    )
    app.dependency_overrides[get_ai_advisor_service] = lambda: service
    try:
        response = client.post(
            "/api/ai/chat",
            headers=headers,
            json={
                "message": (
                    "I want to buy a $2,000 computer within two months, a $4,000 "
                    "RTX 5090 within three months, an $80,000 Mercedes within "
                    "ten years, and a $500,000 house within twenty years."
                )
            },
        )
    finally:
        app.dependency_overrides.pop(get_ai_advisor_service, None)

    assert response.status_code == 200
    assert len(service.extraction_messages) == 2
    assert "Correction required" in service.extraction_messages[1]
    prompt = service.messages[0]
    assert "Recognized goals (4)" in prompt
    assert "Ask exactly these 4 numbered, labelled questions" in prompt
    assert prompt.count("Next MyGoals field: current_amount") == 4
    for title in ["Computer", "RTX 5090", "Mercedes", "House"]:
        assert title in prompt
