from datetime import date
from decimal import Decimal

from app.services.financial_service import FinancialPlanningSnapshot
from app.services.goal_planning_service import (
    build_goal_question_context,
    build_goal_state_correction_prompt,
    build_goal_state_extraction_prompt,
    goal_state_payload_is_complete,
    normalize_goal_planning_state,
)


def financial_snapshot(
    *,
    has_records: bool = True,
    monthly_income: str = "5000",
    monthly_expenses: str = "3200",
    one_off_income: str = "1000",
    one_off_expenses: str = "300",
) -> FinancialPlanningSnapshot:
    return FinancialPlanningSnapshot(
        has_financial_records=has_records,
        has_cash_flow_records=has_records,
        total_assets=Decimal("20000"),
        total_debts=Decimal("4000"),
        cash_savings=Decimal("8000"),
        ongoing_monthly_income=Decimal(monthly_income),
        ongoing_monthly_expenses=Decimal(monthly_expenses),
        one_off_period="2026-07" if has_records else None,
        one_off_income=Decimal(one_off_income),
        one_off_expenses=Decimal(one_off_expenses),
    )


def test_goal_planning_asks_one_mygoals_question_at_a_time():
    state = normalize_goal_planning_state(
        {
            "goals": [
                {
                    "category": "emergency_fund",
                    "answered_fields": ["essential_monthly_expenses"],
                    "essential_monthly_expenses": 2400,
                    "priority": None,
                }
            ],
            "finished_adding_goals": False,
        }
    )

    context = build_goal_question_context(
        state,
        financial_snapshot(),
        as_of=date(2026, 7, 14),
    )

    assert "Next MyGoals field: coverage_months" in context
    assert "How many months do you want to cover?" in context
    assert "Do not ask any additional question" in context


def test_budget_reuses_known_homepage_income():
    state = normalize_goal_planning_state(
        {
            "goals": [
                {
                    "category": "budget",
                    "answered_fields": [],
                    "priority": None,
                }
            ],
            "finished_adding_goals": False,
        }
    )

    context = build_goal_question_context(
        state,
        financial_snapshot(),
        as_of=date(2026, 7, 14),
    )

    assert "Next MyGoals field: fixed_expenses" in context
    assert "reuse the HomePage ongoing monthly income" in context
    assert "Ask exactly this one question: What is your monthly income?" not in context


def test_goal_planning_requires_pdf_without_financial_foundation():
    context = build_goal_question_context(
        None,
        financial_snapshot(has_records=False),
        as_of=date(2026, 7, 14),
    )

    assert "Stage: financial foundation required" in context
    assert "upload a bank statement or transaction PDF" in context
    assert "+ button in AI Chat" in context
    assert "Do not ask a goal-detail question" in context


def complete_general_goal(
    *,
    title: str,
    priority: str | None,
    confirm_priority: bool,
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
        "target_amount": 12000,
        "deadline": "2027-07-14",
        "current_amount": 2000,
        "monthly_contribution": 500,
        "priority": priority,
    }


def test_priority_is_ignored_until_the_user_explicitly_confirms_it():
    state = normalize_goal_planning_state(
        {
            "goals": [
                complete_general_goal(
                    title="Car",
                    priority="High",
                    confirm_priority=False,
                )
            ],
            "finished_adding_goals": True,
        }
    )

    assert state.goals[0].priority is None
    context = build_goal_question_context(
        state,
        financial_snapshot(),
        as_of=date(2026, 7, 14),
    )
    assert "Next MyGoals field: priority" in context
    assert "which priority do you choose" in context
    assert "Do not choose, recommend, or imply any priority" in context


def test_a_single_incomplete_goal_still_gets_one_labelled_question():
    state = normalize_goal_planning_state(
        {
            "goals": [
                complete_general_goal(
                    title="Car",
                    priority="High",
                    confirm_priority=True,
                ),
                {
                    "category": "general_saving",
                    "answered_fields": ["goal_title"],
                    "goal_title": "Travel",
                    "priority": None,
                },
            ],
            "finished_adding_goals": True,
        }
    )

    context = build_goal_question_context(
        state,
        financial_snapshot(),
        as_of=date(2026, 7, 14),
    )
    assert "Stage: collect goal 2 details" in context
    assert "Question 1 — Goal 2: Travel" in context
    assert "Next MyGoals field: target_amount" in context


def test_completed_goals_confirm_whether_another_goal_should_be_added():
    state = normalize_goal_planning_state(
        {
            "goals": [
                complete_general_goal(
                    title="Car",
                    priority="Medium",
                    confirm_priority=True,
                )
            ],
            "finished_adding_goals": False,
        }
    )

    context = build_goal_question_context(
        state,
        financial_snapshot(),
        as_of=date(2026, 7, 14),
    )
    assert "Stage: confirm the goal list" in context
    assert "Would you like to add another goal" in context


def test_relative_deadline_is_normalized_and_not_asked_again():
    state = normalize_goal_planning_state(
        {
            "goals": [
                {
                    "category": "general_saving",
                    "answered_fields": [
                        "goal_title",
                        "target_amount",
                        "deadline",
                    ],
                    "goal_title": "Computer",
                    "target_amount": 2000,
                    "deadline": "within two months",
                    "priority": None,
                }
            ],
            "finished_adding_goals": True,
        },
        as_of=date(2026, 7, 14),
    )

    assert state.goals[0].answers["deadline"] == date(2026, 9, 14)
    context = build_goal_question_context(
        state,
        financial_snapshot(),
        as_of=date(2026, 7, 14),
    )
    assert "Next MyGoals field: current_amount" in context
    assert "Next MyGoals field: deadline" not in context


def test_four_incomplete_goals_are_questioned_together():
    goals = []
    for title, amount, deadline in [
        ("Computer", 2000, "within two months"),
        ("RTX 5090", 4000, "within three months"),
        ("Mercedes", 80000, "within ten years"),
        ("House", 500000, "within twenty years"),
    ]:
        goals.append(
            {
                "category": "general_saving",
                "answered_fields": [
                    "goal_title",
                    "target_amount",
                    "deadline",
                ],
                "goal_title": title,
                "target_amount": amount,
                "deadline": deadline,
                "priority": None,
            }
        )
    state = normalize_goal_planning_state(
        {
            "goals": goals,
            "finished_adding_goals": True,
        },
        as_of=date(2026, 7, 14),
    )

    context = build_goal_question_context(
        state,
        financial_snapshot(),
        as_of=date(2026, 7, 14),
    )

    assert "collect all incomplete goals in parallel" in context
    assert "Recognized goals (4)" in context
    assert "Ask exactly these 4 numbered, labelled questions" in context
    assert context.count("Next MyGoals field: current_amount") == 4
    for goal_index, title in enumerate(
        ["Computer", "RTX 5090", "Mercedes", "House"],
        start=1,
    ):
        assert f"Goal {goal_index}: {title}" in context


def test_goal_extraction_prompt_inventories_every_distinct_goal():
    prompt = build_goal_state_extraction_prompt(
        None,
        (
            "I want a computer in two months, an RTX 5090 in three months, "
            "a Mercedes in ten years, and a house in twenty years."
        ),
    )

    assert "Inventory every distinct goal" in prompt
    assert "goal_count" in prompt
    assert "a computer, a graphics card, a car, and a house are four" in prompt
    assert "relative deadlines" in prompt


def test_goal_count_mismatch_requests_corrected_extraction():
    incomplete_payload = {
        "goal_count": 4,
        "goals": [{"category": "general_saving"}],
        "finished_adding_goals": True,
    }

    assert goal_state_payload_is_complete(incomplete_payload) is False
    correction = build_goal_state_correction_prompt(
        "original extraction prompt",
        incomplete_payload,
    )
    assert "reported goal_count=4 but returned 1 goal objects" in correction
    assert "preserve every distinct goal" in correction
