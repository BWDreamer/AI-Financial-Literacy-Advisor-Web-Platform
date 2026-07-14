from datetime import date
from decimal import Decimal

import pytest

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
        "answered_fields": [
            "goal_title",
            "target_amount",
            "deadline",
            "current_amount",
            "monthly_contribution",
            "priority",
        ],
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
            "finished_adding_goals": True,
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
    assert "Stage: final negotiated allocation" in context
    assert "Recognized goals to cover in the final response: 2" in context
    assert "Do not omit a goal" in context
    assert "Available ongoing monthly surplus for allocation: $900.00" in context
    assert "Available one-off surplus for allocation: $600.00" in context
    assert "Every priority below was explicitly selected by the user" in context
    assert "Goal: Car" in context
    assert "Priority: High" in context
    assert "Goal: Travel" in context
    assert "Priority: Low" in context
    assert "Do not change, merge, or invent these amounts" in context


def test_allocation_rejects_a_goal_without_user_confirmed_priority():
    goal = complete_general_goal(
        title="Car",
        target_amount=12000,
        priority="High",
    )
    goal["answered_fields"].remove("priority")
    state = normalize_goal_planning_state(
        {
            "goals": [goal],
            "finished_adding_goals": True,
        }
    )

    with pytest.raises(ValueError, match="user-confirmed priority"):
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
            "finished_adding_goals": True,
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
