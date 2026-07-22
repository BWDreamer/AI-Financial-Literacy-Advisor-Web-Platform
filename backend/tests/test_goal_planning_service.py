from datetime import date, timedelta
from decimal import Decimal

from app.services.financial_service import FinancialPlanningSnapshot
from app.services.goal_planning_service import (
    GoalRecommendationStatus,
    build_goal_dialogue_context,
    build_goal_state_correction_prompt,
    build_goal_state_extraction_prompt,
    emergency_fund_target_amount,
    goal_state_payload_is_complete,
    normalize_goal_planning_state,
)


def financial_snapshot(*, has_records: bool = True) -> FinancialPlanningSnapshot:
    return FinancialPlanningSnapshot(
        has_financial_records=has_records,
        has_cash_flow_records=has_records,
        total_assets=Decimal("20000") if has_records else Decimal("0"),
        total_debts=Decimal("4000") if has_records else Decimal("0"),
        cash_savings=Decimal("8000") if has_records else Decimal("0"),
        ongoing_monthly_income=Decimal("5000") if has_records else Decimal("0"),
        ongoing_monthly_expenses=Decimal("3200") if has_records else Decimal("0"),
        one_off_period="2026-07" if has_records else None,
        one_off_income=Decimal("1000") if has_records else Decimal("0"),
        one_off_expenses=Decimal("300") if has_records else Decimal("0"),
    )


def complete_general_goal(
    *,
    title: str = "Reliable used car",
    priority: str | None = "Medium",
) -> dict:
    return {
        "category": "general_saving",
        "goal_title": title,
        "target_amount": 15000,
        "deadline": (date.today() + timedelta(days=730)).isoformat(),
        "current_amount": 2000,
        "monthly_contribution": 550,
        "priority": priority,
    }


def complete_state(
    recommendation_status: str = "needs_recommendation",
) -> dict:
    return {
        "goal_count": 1,
        "goals": [complete_general_goal()],
        "recommendation_status": recommendation_status,
    }


def test_goal_extraction_builds_complete_plan_from_memory_and_financial_context():
    prompt = build_goal_state_extraction_prompt(
        (
            "Assistant: What Budget / Cash Flow goal would you like to set?\n"
            "[Financial goal planning mode: category=budget]"
        ),
        "I want to save for a reliable used car.",
        (
            "Long-term user memory:\n"
            "- preference: User prefers balanced and realistic plans.\n"
            "- profile: User is new to financial planning."
        ),
        "Ongoing monthly surplus: $1,800.00.",
    )

    assert "produce a complete proposed plan now" in prompt
    assert "Preference and Profile memory text" in prompt
    assert "User prefers balanced and realistic plans" in prompt
    assert "User is new to financial planning" in prompt
    assert "Ongoing monthly surplus: $1,800.00" in prompt
    assert "Do not ask the user for target amounts" in prompt
    assert "decide all missing amounts" in prompt
    assert "explicit category selection" in prompt
    assert "category=budget" in prompt


def test_complete_goal_plan_payload_requires_ai_selected_details():
    payload = complete_state()

    assert goal_state_payload_is_complete(payload) is True

    payload["goals"][0]["monthly_contribution"] = None
    assert goal_state_payload_is_complete(payload) is False

    correction = build_goal_state_correction_prompt(
        "original extraction prompt",
        payload,
    )
    assert "monthly_contribution" in correction
    assert "Preference/Profile and financial context" in correction


def test_emergency_fund_accepts_direct_target_without_reinterpreting_it():
    direct_target_goal = {
        "category": "emergency_fund",
        "target_amount": 1000,
        "essential_monthly_expenses": None,
        "coverage_months": None,
        "deadline": (date.today() + timedelta(days=180)).isoformat(),
        "current_amount": 0,
        "monthly_contribution": 200,
        "priority": "High",
    }
    payload = {
        "goal_count": 1,
        "goals": [direct_target_goal],
        "recommendation_status": "needs_recommendation",
    }

    assert goal_state_payload_is_complete(payload) is True
    assert emergency_fund_target_amount(direct_target_goal) == Decimal("1000.00")

    direct_target_goal["essential_monthly_expenses"] = 1000
    direct_target_goal["coverage_months"] = 3
    assert emergency_fund_target_amount(direct_target_goal) == Decimal("1000.00")


def test_emergency_fund_expense_model_remains_available_without_direct_target():
    assert emergency_fund_target_amount(
        {
            "essential_monthly_expenses": 1000,
            "coverage_months": 3,
        }
    ) == Decimal("3000.00")


def test_relative_deadline_and_recommendation_status_are_normalized():
    payload = complete_state("accepted")
    payload["goals"][0]["deadline"] = "within two months"

    state = normalize_goal_planning_state(
        payload,
        as_of=date(2026, 7, 14),
    )

    assert state.goals[0].answers["deadline"] == date(2026, 9, 14)
    assert state.goals[0].priority.value == "Medium"
    assert state.recommendation_status == GoalRecommendationStatus.ACCEPTED


def test_rejected_recommendation_asks_only_one_macro_question():
    state = normalize_goal_planning_state(complete_state("rejected"))

    context = build_goal_dialogue_context(state, financial_snapshot())

    assert "Stage: recommendation rejected; collect macro direction" in context
    assert "ask exactly one concise macro-level question" in context
    assert "faster progress" in context
    assert "Do not ask for target amounts, saved amounts" in context
    assert "do not propose the revised plan" in context


def test_missing_financial_records_do_not_block_the_first_recommendation():
    context = build_goal_dialogue_context(
        None,
        financial_snapshot(has_records=False),
    )

    assert "Stage: complete recommendation awaiting approval" in context
    assert "Give the user one complete best recommendation immediately" in context
    assert "conservative, clearly labelled planning assumptions" in context
    assert "Does this overall plan work for you?" in context
    assert "upload" not in context.lower()


def test_goal_count_mismatch_requests_corrected_extraction():
    incomplete_payload = {
        "goal_count": 4,
        "goals": [complete_general_goal(title="Computer")],
        "recommendation_status": "needs_recommendation",
    }

    assert goal_state_payload_is_complete(incomplete_payload) is False
    correction = build_goal_state_correction_prompt(
        "original extraction prompt",
        incomplete_payload,
    )
    assert "reported goal_count=4 but returned 1 goal objects" in correction
    assert "preserve every distinct goal" in correction
