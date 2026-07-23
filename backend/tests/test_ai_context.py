from datetime import date, timedelta

from app.ai.dependencies import get_ai_advisor_service
from app.main import app
from app.models.financial import CashBucket
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


class IntentClarificationAdvisorService(GoalPlanningAdvisorService):
    def __init__(
        self,
        planned_state: dict,
        clarification_payloads: list[dict],
    ) -> None:
        super().__init__(planned_state)
        self.clarification_payloads = clarification_payloads
        self.clarification_messages: list[str] = []

    async def reply_json(
        self,
        message: str,
        response_schema: dict,
    ) -> dict:
        if message.startswith(
            "Classify whether the user's goal-planning intent is semantically ambiguous"
        ):
            del response_schema
            index = len(self.clarification_messages)
            self.clarification_messages.append(message)
            return self.clarification_payloads[
                min(index, len(self.clarification_payloads) - 1)
            ]
        return await super().reply_json(message, response_schema)


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
        goals_before_confirmation = client.get(
            "/api/goals",
            headers=headers,
        ).json()
        second_response = client.post(
            "/api/ai/chat",
            headers=headers,
            json={
                "message": "Yes, that overall plan works for me.",
                "conversation_id": conversation_id,
            },
        )
        repeated_confirmation = client.post(
            "/api/ai/chat",
            headers=headers,
            json={
                "message": "Yes, I confirm the same plan.",
                "conversation_id": conversation_id,
            },
        )
        saved_goals = client.get(
            "/api/goals",
            headers=headers,
        ).json()
    finally:
        app.dependency_overrides.pop(get_ai_advisor_service, None)

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert repeated_confirmation.status_code == 200
    assert goals_before_confirmation == []
    assert len(saved_goals) == 1
    assert saved_goals[0]["name"] == "Reliable used car"
    assert saved_goals[0]["category"] == "General Saving"
    assert saved_goals[0]["target_amount"] == "15000.00"
    assert saved_goals[0]["current_amount"] == "0.00"
    assert saved_goals[0]["monthly_contribution"] == "625.00"
    assert saved_goals[0]["allocated_monthly"] == "625.00"
    assert saved_goals[0]["status"] == "on_track"
    assert saved_goals[0]["priority"] == 3
    final_prompt = service.messages[1]
    assert "Earlier messages in this same conversation" in final_prompt
    assert "Stage: confirmed goal plan" in final_prompt
    assert "planning is complete" in final_prompt
    assert "every agreed goal is now available in MyGoals" in final_prompt
    assert "Does this overall plan work for you?" not in final_prompt
    assert "Do not ask another question" in final_prompt


def test_confirmed_plan_is_persisted_with_exact_my_goals_allocations(
    client,
    db_session,
):
    headers = authorization_headers(client, "confirmed-allocations@example.com")
    today = date.today()
    for endpoint, payload in [
        (
            "/api/financials/assets",
            {
                "asset_type": "cash",
                "name": "Opening balance",
                "amount": 12500,
            },
        ),
        (
            "/api/financials/cash-flows",
            {
                "flow_type": "income",
                "name": "Imported monthly income",
                "amount": 3800,
                "ongoing_amount": 3000,
                "date": today.isoformat(),
            },
        ),
        (
            "/api/financials/cash-flows",
            {
                "flow_type": "expense",
                "name": "Imported monthly expenses",
                "amount": 1710,
                "ongoing_amount": 1710,
                "date": today.isoformat(),
            },
        ),
    ]:
        assert client.post(endpoint, headers=headers, json=payload).status_code == 201

    planned_goals = [
        {
            "category": "emergency_fund",
            "target_amount": 6000,
            "essential_monthly_expenses": None,
            "coverage_months": None,
            "deadline": today.replace(year=today.year + 1).isoformat(),
            "current_amount": 0,
            "monthly_contribution": 0,
            "priority": "High",
        },
        {
            "category": "general_saving",
            "goal_title": "Reliable used car",
            "target_amount": 15000,
            "deadline": today.replace(year=today.year + 2).isoformat(),
            "current_amount": 0,
            "monthly_contribution": 0,
            "priority": "Medium",
        },
    ]
    conversation_id = create_conversation(client, headers)
    service = SequencedGoalPlanningAdvisorService(
        [
            goal_state("needs_recommendation", planned_goals),
            goal_state("accepted", planned_goals),
        ]
    )
    app.dependency_overrides[get_ai_advisor_service] = lambda: service
    try:
        client.post(
            "/api/ai/chat",
            headers=headers,
            json={
                "message": "Plan my emergency fund and car savings.",
                "conversation_id": conversation_id,
            },
        )
        response = client.post(
            "/api/ai/chat",
            headers=headers,
            json={
                "message": "Yes, I confirm this plan.",
                "conversation_id": conversation_id,
            },
        )
        saved_goals = client.get("/api/goals", headers=headers).json()
        allocation = client.get(
            "/api/goals/allocation-settings",
            headers=headers,
        ).json()
        summary = client.get("/api/goals/summary", headers=headers).json()
    finally:
        app.dependency_overrides.pop(get_ai_advisor_service, None)

    assert response.status_code == 200
    goals_by_name = {goal["name"]: goal for goal in saved_goals}
    emergency = goals_by_name["Emergency Fund"]
    car = goals_by_name["Reliable used car"]

    assert emergency["current_amount"] == "480.00"
    assert emergency["progress_percentage"] == "8.00"
    assert emergency["monthly_contribution"] == "460.00"
    assert emergency["allocated_monthly"] == "460.00"
    assert emergency["status"] == "on_track"

    assert car["current_amount"] == "320.00"
    assert car["progress_percentage"] == "2.13"
    assert car["monthly_contribution"] == "611.67"
    assert car["allocated_monthly"] == "611.67"
    assert car["status"] == "on_track"

    monthly_allocation = allocation["monthly_allocation"]
    assert monthly_allocation["monthly_net_income"] == "1290.00"
    assert monthly_allocation["monthly_allocatable"] == "1290.00"
    assert monthly_allocation["already_assigned"] == "1071.67"
    assert monthly_allocation["unassigned"] == "218.33"
    assert summary["cash_savings"] == "14590.00"
    assert summary["cash_already_assigned"] == "800.00"
    assert summary["monthly_net_income"] == "1290.00"
    assert summary["monthly_unassigned"] == "218.33"
    cash_buckets = db_session.query(CashBucket).filter(
        CashBucket.goal_id.in_([emergency["id"], car["id"]])
    ).all()
    assert sorted(
        (bucket.name, str(bucket.amount))
        for bucket in cash_buckets
    ) == [
        ("Emergency Fund", "480.00"),
        ("Reliable used car", "320.00"),
    ]

    for goal, expected_amount in [
        (emergency, "480.00"),
        (car, "320.00"),
    ]:
        progress = client.get(
            f"/api/goals/{goal['id']}/progress",
            headers=headers,
        ).json()
        assert len(progress) == 1
        assert progress[0]["amount"] == expected_amount
        assert progress[0]["source"] == "ai_plan_one_off"


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


def emergency_fund_state(
    recommendation_status: str = "needs_recommendation",
) -> dict:
    return {
        "goal_count": 1,
        "goals": [
            {
                "category": "emergency_fund",
                "target_amount": 1000,
                "essential_monthly_expenses": None,
                "coverage_months": None,
                "deadline": (date.today() + timedelta(days=180)).isoformat(),
                "current_amount": 0,
                "monthly_contribution": 200,
                "priority": "High",
            }
        ],
        "recommendation_status": recommendation_status,
    }


def add_emergency_fund_category_prompt(
    client,
    headers: dict[str, str],
    conversation_id: int,
) -> None:
    response = client.post(
        f"/api/chat/conversations/{conversation_id}/messages",
        headers=headers,
        json={
            "role": "assistant",
            "content": (
                "What Emergency Fund goal would you like to set?\n\n"
                "[Financial goal planning mode: category=emergency_fund]"
            ),
        },
    )
    assert response.status_code == 201


def test_bare_emergency_amount_is_confirmed_remembered_and_never_multiplied(client):
    headers = authorization_headers(client, "emergency-intent@example.com")
    add_goal_planning_cash_flow(client, headers)
    conversation_id = create_conversation(client, headers)
    add_emergency_fund_category_prompt(client, headers, conversation_id)
    service = SequencedGoalPlanningAdvisorService(
        [
            emergency_fund_state(),
            emergency_fund_state("accepted"),
        ]
    )
    app.dependency_overrides[get_ai_advisor_service] = lambda: service
    try:
        ambiguous_response = client.post(
            "/api/ai/chat",
            headers=headers,
            json={"message": "$1000", "conversation_id": conversation_id},
        )
        assert client.get("/api/memory", headers=headers).json() == []

        resolved_response = client.post(
            "/api/ai/chat",
            headers=headers,
            json={
                "message": "That is my target amount.",
                "conversation_id": conversation_id,
            },
        )
        confirmation_response = client.post(
            "/api/ai/chat",
            headers=headers,
            json={"message": "Yes, keep that plan.", "conversation_id": conversation_id},
        )
        saved_goals = client.get("/api/goals", headers=headers).json()

        new_conversation_id = create_conversation(client, headers)
        recall_response = client.post(
            "/api/ai/chat",
            headers=headers,
            json={
                "message": "What is my Emergency Fund target amount?",
                "conversation_id": new_conversation_id,
            },
        )
    finally:
        app.dependency_overrides.pop(get_ai_advisor_service, None)

    assert ambiguous_response.status_code == 200
    assert ambiguous_response.json()["answer"] == (
        "Is $1,000 your Emergency Fund target amount, or your essential monthly "
        "expenses?"
    )
    assert resolved_response.status_code == 200
    assert confirmation_response.status_code == 200
    assert recall_response.status_code == 200
    assert len(service.extraction_messages) == 2
    assert "The user's Emergency Fund target amount is $1,000.00" in (
        service.extraction_messages[0]
    )
    assert "The user's Emergency Fund target amount is $1,000.00" in (
        service.extraction_messages[1]
    )
    assert "Target amount: $1,000.00" in service.messages[0]
    assert "Target amount: $3,000.00" not in service.messages[0]
    assert len(saved_goals) == 1
    assert saved_goals[0]["target_amount"] == "1000.00"
    memories = client.get("/api/memory", headers=headers).json()
    assert len(memories) == 1
    assert memories[0]["category"] == "goal"
    assert memories[0]["fact"] == (
        "The user's Emergency Fund target amount is $1,000.00."
    )
    assert "The user's Emergency Fund target amount is $1,000.00" in (
        service.messages[-1]
    )


def test_ambiguous_goal_sentence_is_queried_then_confirmed_into_memory(client):
    headers = authorization_headers(client, "sentence-intent@example.com")
    conversation_id = create_conversation(client, headers)
    add_emergency_fund_category_prompt(client, headers, conversation_id)
    service = IntentClarificationAdvisorService(
        emergency_fund_state(),
        [
            {
                "status": "needs_clarification",
                "clarifying_question": (
                    "Does $1,000 mean your total Emergency Fund target or one "
                    "month of essential expenses?"
                ),
                "confirmed_fact": None,
                "memory_category": None,
            },
            {
                "status": "resolved",
                "clarifying_question": None,
                "confirmed_fact": (
                    "The user's Emergency Fund target amount is $1,000.00."
                ),
                "memory_category": "goal",
            },
        ],
    )
    app.dependency_overrides[get_ai_advisor_service] = lambda: service
    try:
        first_response = client.post(
            "/api/ai/chat",
            headers=headers,
            json={
                "message": "I want my Emergency Fund based on $1,000.",
                "conversation_id": conversation_id,
            },
        )
        memories_before_confirmation = client.get(
            "/api/memory",
            headers=headers,
        ).json()
        second_response = client.post(
            "/api/ai/chat",
            headers=headers,
            json={
                "message": "I mean the total buffer I want.",
                "conversation_id": conversation_id,
            },
        )
        memories_after_confirmation = client.get(
            "/api/memory",
            headers=headers,
        ).json()
    finally:
        app.dependency_overrides.pop(get_ai_advisor_service, None)

    assert first_response.status_code == 200
    assert first_response.json()["answer"].startswith("Does $1,000 mean")
    assert memories_before_confirmation == []
    assert service.extraction_messages
    assert second_response.status_code == 200
    assert len(memories_after_confirmation) == 1
    assert memories_after_confirmation[0]["fact"] == (
        "The user's Emergency Fund target amount is $1,000.00."
    )


def test_clear_goal_intent_is_automatically_written_to_memory(client):
    headers = authorization_headers(client, "clear-intent@example.com")
    conversation_id = create_conversation(client, headers)
    add_emergency_fund_category_prompt(client, headers, conversation_id)
    service = IntentClarificationAdvisorService(
        emergency_fund_state(),
        [
            {
                "status": "resolved",
                "clarifying_question": None,
                "confirmed_fact": (
                    "The user's Emergency Fund target amount is $1,000.00."
                ),
                "memory_category": "goal",
            }
        ],
    )
    app.dependency_overrides[get_ai_advisor_service] = lambda: service
    try:
        response = client.post(
            "/api/ai/chat",
            headers=headers,
            json={
                "message": "My Emergency Fund target amount is $1,000.",
                "conversation_id": conversation_id,
            },
        )
        memories = client.get("/api/memory", headers=headers).json()
    finally:
        app.dependency_overrides.pop(get_ai_advisor_service, None)

    assert response.status_code == 200
    assert len(service.clarification_messages) == 1
    assert len(service.extraction_messages) == 1
    assert len(memories) == 1
    assert memories[0]["source"] == "chat"
    assert memories[0]["fact"] == (
        "The user's Emergency Fund target amount is $1,000.00."
    )
