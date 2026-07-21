from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from types import SimpleNamespace

import pytest

from app.models.goal import Goal, GoalProgress
from app.schemas.goal import GoalPreviewRequest
from app.services.goal_service import (
    add_months,
    analyse_goal,
    build_goal_chart,
    build_goal_preview,
    calculate_monthly_allocation,
    months_until,
    refresh_goal_status,
    validate_owned_ratios,
)


def make_goal(
    *,
    target_amount: Decimal = Decimal("1200"),
    current_amount: Decimal = Decimal("200"),
    monthly_contribution: Decimal = Decimal("250"),
    target_date: date = date(2026, 12, 31),
) -> SimpleNamespace:
    return SimpleNamespace(
        target_amount=target_amount,
        current_amount=current_amount,
        monthly_contribution=monthly_contribution,
        target_date=target_date,
    )


def test_months_until_and_add_months_handle_month_boundaries():
    assert months_until(date(2026, 8, 20), today=date(2026, 7, 21)) == 0
    assert months_until(date(2026, 8, 21), today=date(2026, 7, 21)) == 1
    assert months_until(date(2025, 1, 1), today=date(2026, 7, 21)) == 0

    assert add_months(date(2026, 1, 31), 1) == date(2026, 2, 28)
    assert add_months(date(2026, 12, 31), 2) == date(2027, 2, 28)


def test_analyse_goal_marks_completed_on_track_and_behind_states():
    completed = analyse_goal(
        make_goal(
            target_amount=Decimal("1000"),
            current_amount=Decimal("1000"),
            monthly_contribution=Decimal("0"),
            target_date=date(2026, 12, 31),
        ),
        today=date(2026, 7, 21),
    )
    assert completed["status"] == "completed"
    assert completed["progress_percentage"] == Decimal("100.00")

    on_track = analyse_goal(
        make_goal(
            target_amount=Decimal("1200"),
            current_amount=Decimal("200"),
            monthly_contribution=Decimal("250"),
            target_date=date(2026, 12, 31),
        ),
        today=date(2026, 7, 21),
    )
    assert on_track["status"] == "on_track"
    assert on_track["required_monthly"] == Decimal("200.00")
    assert on_track["monthly_difference"] == Decimal("50.00")

    behind = analyse_goal(
        make_goal(
            target_amount=Decimal("1200"),
            current_amount=Decimal("200"),
            monthly_contribution=Decimal("100"),
            target_date=date(2026, 12, 31),
        ),
        today=date(2026, 7, 21),
    )
    assert behind["status"] == "behind"
    assert behind["projected_completion_date"] == date(2027, 5, 21)


def test_refresh_goal_status_updates_goal_from_analysis():
    goal = Goal(
        user_id=1,
        name="Trip",
        category="Saving",
        target_amount=Decimal("1000"),
        current_amount=Decimal("0"),
        monthly_contribution=Decimal("0"),
        target_date=date(2025, 1, 1),
    )

    refresh_goal_status(goal)

    assert goal.status == "behind"


def test_build_goal_preview_calculates_category_specific_goal_values():
    preview = build_goal_preview(
        GoalPreviewRequest(
            category="Emergency Fund",
            priority="High",
            target_date=date(2026, 12, 31),
            category_details={
                "essential_monthly_expenses": "2500",
                "coverage_months": "3",
                "current_amount": "1000",
                "monthly_contribution": "500",
            },
        )
    )

    assert preview["goal"].name == "Emergency Fund"
    assert preview["goal"].target_amount == Decimal("7500")
    assert preview["goal"].current_amount == Decimal("1000")
    assert preview["goal"].priority == 1
    assert preview["analysis"]["status"] in {"on_track", "behind", "completed"}


def test_build_goal_preview_rejects_unknown_category_and_invalid_numbers():
    with pytest.raises(ValueError, match="Unsupported goal category"):
        build_goal_preview(
            GoalPreviewRequest(
                category="Unknown",
                target_date=date(2026, 12, 31),
                category_details={},
            )
        )

    with pytest.raises(InvalidOperation):
        build_goal_preview(
            GoalPreviewRequest(
                category="Emergency Fund",
                target_date=date(2026, 12, 31),
                category_details={
                    "essential_monthly_expenses": "not-a-number",
                    "coverage_months": "3",
                },
            )
        )


def test_validate_owned_ratios_rejects_ratios_for_unowned_goals():
    validate_owned_ratios(
        goals=[SimpleNamespace(id=1), SimpleNamespace(id=2)],
        ratios=[SimpleNamespace(goal_id=1)],
    )

    with pytest.raises(ValueError, match="Goals not found: \\[3\\]"):
        validate_owned_ratios(
            goals=[SimpleNamespace(id=1), SimpleNamespace(id=2)],
            ratios=[SimpleNamespace(goal_id=3)],
        )


def test_calculate_monthly_allocation_uses_positive_net_income_only():
    allocation = calculate_monthly_allocation(
        finance={
            "monthly_income": Decimal("5000"),
            "monthly_expenses": Decimal("3000"),
        },
        ratio=Decimal("50"),
        goal_ratios=[
            {"goal_id": 1, "ratio": Decimal("25")},
            SimpleNamespace(goal_id=2, ratio=Decimal("50")),
        ],
    )

    assert allocation["monthly_net_income"] == Decimal("2000.00")
    assert allocation["monthly_allocatable"] == Decimal("1000.00")
    assert allocation["already_assigned"] == Decimal("750.00")
    assert allocation["unassigned"] == Decimal("250.00")
    assert allocation["goals"] == [
        {"goal_id": 1, "ratio": Decimal("25"), "monthly_amount": Decimal("250.00")},
        {"goal_id": 2, "ratio": Decimal("50"), "monthly_amount": Decimal("500.00")},
    ]

    no_surplus = calculate_monthly_allocation(
        finance={
            "monthly_income": Decimal("2000"),
            "monthly_expenses": Decimal("3000"),
        },
        ratio=Decimal("50"),
        goal_ratios=[{"goal_id": 1, "ratio": Decimal("100")}],
    )
    assert no_surplus["monthly_net_income"] == Decimal("0.00")
    assert no_surplus["monthly_allocatable"] == Decimal("0.00")


def test_build_goal_chart_uses_progress_history_and_expected_target_points(db_session):
    goal = Goal(
        user_id=1,
        name="Emergency",
        category="Saving",
        target_amount=Decimal("1200"),
        current_amount=Decimal("500"),
        monthly_contribution=Decimal("100"),
        target_date=date(2026, 4, 15),
        created_at=datetime(2026, 1, 15),
    )
    db_session.add(goal)
    db_session.flush()
    db_session.add_all(
        [
            GoalProgress(
                goal_id=goal.id,
                amount=Decimal("100"),
                progress_date=date(2026, 2, 15),
                new_current_amount=Decimal("400"),
            ),
            GoalProgress(
                goal_id=goal.id,
                amount=Decimal("200"),
                progress_date=date(2026, 3, 15),
                new_current_amount=Decimal("500"),
            ),
        ]
    )
    db_session.commit()

    chart = build_goal_chart(db_session, goal)

    assert chart["target_amount"] == Decimal("1200")
    assert chart["actual_progress_points"] == [
        {"date": date(2026, 1, 15), "amount": Decimal("200.00")},
        {"date": date(2026, 2, 15), "amount": Decimal("300.00")},
        {"date": date(2026, 3, 15), "amount": Decimal("500.00")},
    ]
    assert chart["expected_progress_points"][0] == {
        "date": date(2026, 1, 15),
        "amount": Decimal("0.00"),
    }
    assert chart["expected_progress_points"][-1] == {
        "date": date(2026, 4, 15),
        "amount": Decimal("1200.00"),
    }
