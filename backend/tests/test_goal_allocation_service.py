from datetime import date
from decimal import Decimal

import pytest

from app.core.config import settings
from app.services.financial_service import FinancialPlanningSnapshot
from app.services.goal_allocation_service import (
    build_goal_allocation_context,
    calculate_goal_allocations,
)
from app.services.goal_planning_service import (
    GoalCategory,
    normalize_goal_planning_state,
)


def financial_snapshot() -> FinancialPlanningSnapshot:
    return FinancialPlanningSnapshot(
        has_financial_records=True,
        has_cash_flow_records=True,
        total_assets=Decimal("20000"),
        total_debts=Decimal("4000"),
        cash_savings=Decimal("8000"),
        ongoing_monthly_income=Decimal("5000"),
        ongoing_monthly_expenses=Decimal("4100"),
        one_off_period="2026-07",
        one_off_income=Decimal("1000"),
        one_off_expenses=Decimal("400"),
    )


def complete_general_goal(
    *,
    title: str,
    target_amount: int,
    priority: str,
    deadline: str = "2027-07-14",
) -> dict:
    return {
        "category": GoalCategory.GENERAL_SAVING.value,
        "goal_title": title,
        "target_amount": target_amount,
        "deadline": deadline,
        "current_amount": 0,
        "monthly_contribution": 500,
        "priority": priority,
    }


def test_allocation_keeps_one_off_and_recurring_surplus_separate():
    state = normalize_goal_planning_state(
        {
            "goals": [
                complete_general_goal(
                    title="Car",
                    target_amount=12000,
                    priority="High",
                ),
                complete_general_goal(
                    title="Travel",
                    target_amount=6000,
                    priority="Low",
                ),
            ],
            "recommendation_status": "accepted",
        }
    )
    snapshot = financial_snapshot()

    allocations, recurring_left, one_off_left = calculate_goal_allocations(
        state,
        snapshot,
        as_of=date(2026, 7, 14),
    )

    assert len(allocations) == 2
    assert sum(
        (row.recurring_monthly_amount for row in allocations), Decimal()
    ) == Decimal("900.00")
    assert sum(
        (row.one_off_amount for row in allocations), Decimal()
    ) == Decimal("600.00")
    assert (
        allocations[0].recurring_monthly_amount
        > allocations[1].recurring_monthly_amount
    )
    assert allocations[0].one_off_amount > allocations[1].one_off_amount
    assert allocations[0].one_off_amount == Decimal("450.00")
    assert allocations[1].one_off_amount == Decimal("150.00")
    assert allocations[0].recurring_monthly_amount == Decimal("675.00")
    assert allocations[1].recurring_monthly_amount == Decimal("225.00")
    assert recurring_left == Decimal("0.00")
    assert one_off_left == Decimal("0.00")

    context = build_goal_allocation_context(
        state,
        snapshot,
        as_of=date(2026, 7, 14),
    )
    assert "Stage: confirmed goal plan" in context
    assert "Recognized goals to cover in the final response: 2" in context
    assert "Do not omit a goal" in context
    assert "Available ongoing monthly surplus for allocation: $900.00" in context
    assert "Available one-off surplus for allocation: $600.00" in context
    assert "the AI selected them using the Preference/Profile memory" in context
    assert "Goal: Car" in context
    assert "Priority: High" in context
    assert "Goal: Travel" in context
    assert "Priority: Low" in context
    assert "Do not change, merge, or invent these amounts" in context


def test_allocation_rejects_a_goal_without_planning_priority():
    goal = complete_general_goal(
        title="Car",
        target_amount=12000,
        priority="High",
    )
    goal["priority"] = None
    state = normalize_goal_planning_state(
        {
            "goals": [goal],
            "recommendation_status": "accepted",
        }
    )

    with pytest.raises(ValueError, match="planning priority"):
        calculate_goal_allocations(
            state,
            financial_snapshot(),
            as_of=date(2026, 7, 14),
        )


def test_allocation_distributes_surplus_across_four_goals():
    state = normalize_goal_planning_state(
        {
            "goals": [
                complete_general_goal(
                    title="Computer",
                    target_amount=2000,
                    priority="High",
                    deadline="2026-09-14",
                ),
                complete_general_goal(
                    title="RTX 5090",
                    target_amount=4000,
                    priority="Medium",
                    deadline="2026-10-14",
                ),
                complete_general_goal(
                    title="Mercedes",
                    target_amount=80000,
                    priority="Medium",
                    deadline="2036-07-14",
                ),
                complete_general_goal(
                    title="House",
                    target_amount=500000,
                    priority="Low",
                    deadline="2046-07-14",
                ),
            ],
            "recommendation_status": "accepted",
        }
    )

    allocations, recurring_left, _ = calculate_goal_allocations(
        state,
        financial_snapshot(),
        as_of=date(2026, 7, 14),
    )

    assert [allocation.goal.name for allocation in allocations] == [
        "Computer",
        "RTX 5090",
        "Mercedes",
        "House",
    ]
    assert all(
        allocation.recurring_monthly_amount > Decimal("0.00")
        for allocation in allocations
    )
    assert sum(
        (
            allocation.recurring_monthly_amount
            for allocation in allocations
        ),
        Decimal("0.00"),
    ) == Decimal("900.00")
    assert recurring_left == Decimal("0.00")


def test_allocation_uses_configured_priority_weights(monkeypatch):
    monkeypatch.setattr(
        settings,
        "goal_priority_high_weight",
        Decimal("5"),
    )
    monkeypatch.setattr(
        settings,
        "goal_priority_medium_weight",
        Decimal("2"),
    )
    monkeypatch.setattr(
        settings,
        "goal_priority_low_weight",
        Decimal("1"),
    )
    state = normalize_goal_planning_state(
        {
            "goals": [
                complete_general_goal(
                    title="Car",
                    target_amount=12000,
                    priority="High",
                ),
                complete_general_goal(
                    title="Travel",
                    target_amount=6000,
                    priority="Low",
                ),
            ],
            "recommendation_status": "accepted",
        }
    )

    allocations, _, _ = calculate_goal_allocations(
        state,
        financial_snapshot(),
        as_of=date(2026, 7, 14),
    )
    context = build_goal_allocation_context(
        state,
        financial_snapshot(),
        as_of=date(2026, 7, 14),
    )

    assert allocations[0].one_off_amount == Decimal("500.00")
    assert allocations[1].one_off_amount == Decimal("100.00")
    assert allocations[0].recurring_monthly_amount == Decimal("750.00")
    assert allocations[1].recurring_monthly_amount == Decimal("150.00")
    assert "High=5, Medium=2, and Low=1 weights" in context


def test_initial_recommendation_is_complete_and_only_requests_approval():
    state = normalize_goal_planning_state(
        {
            "goals": [
                complete_general_goal(
                    title="Car",
                    target_amount=12000,
                    priority="Medium",
                )
            ],
            "recommendation_status": "needs_recommendation",
        }
    )

    context = build_goal_allocation_context(
        state,
        financial_snapshot(),
        as_of=date(2026, 7, 14),
        awaiting_approval=True,
    )

    assert "Stage: complete recommendation awaiting approval" in context
    assert "Present one complete best recommendation immediately" in context
    assert "Target amount: $12,000.00" in context
    assert "Planning monthly amount: $500.00" in context
    assert "Does this overall plan work for you?" in context
    assert "Do not ask any other question" in context


def test_unverified_finances_use_deadline_requirement_as_an_assumption():
    state = normalize_goal_planning_state(
        {
            "goals": [
                complete_general_goal(
                    title="Car",
                    target_amount=12000,
                    priority="Medium",
                )
            ],
            "recommendation_status": "needs_recommendation",
        }
    )
    snapshot = FinancialPlanningSnapshot(
        has_financial_records=False,
        has_cash_flow_records=False,
        total_assets=Decimal("0"),
        total_debts=Decimal("0"),
        cash_savings=Decimal("0"),
        ongoing_monthly_income=Decimal("0"),
        ongoing_monthly_expenses=Decimal("0"),
        one_off_period=None,
        one_off_income=Decimal("0"),
        one_off_expenses=Decimal("0"),
    )

    allocations, recurring_left, _ = calculate_goal_allocations(
        state,
        snapshot,
        as_of=date(2026, 7, 14),
    )
    context = build_goal_allocation_context(
        state,
        snapshot,
        as_of=date(2026, 7, 14),
        awaiting_approval=True,
    )

    assert allocations[0].recurring_monthly_amount == Decimal("1000.00")
    assert recurring_left == Decimal("0.00")
    assert "illustrative requirement" in context
    assert "not as proven affordability" in context
