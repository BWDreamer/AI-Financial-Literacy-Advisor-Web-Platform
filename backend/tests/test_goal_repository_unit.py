from datetime import date
from decimal import Decimal

import pytest

from app.repositories.goal_repository import (
    delete_goal,
    delete_progress,
    get_allocation_settings,
    get_goal,
    list_goals,
    list_progress,
    save_allocation_settings,
    save_goal,
    save_progress,
)
from app.repositories.user_repository import create_user
from app.schemas.goal import (
    AllocationSettingsRequest,
    GoalProgressRequest,
    GoalRequest,
)


def goal_request(name: str = "Emergency fund", priority: int = 1) -> GoalRequest:
    return GoalRequest(
        name=name,
        category="Saving",
        target_amount=Decimal("10000"),
        current_amount=Decimal("1000"),
        monthly_contribution=Decimal("500"),
        target_date=date(2026, 12, 31),
        priority=priority,
    )


def test_save_goal_creates_updates_lists_and_deletes_goal(db_session):
    user = create_user(db_session, email="goal@example.com", password_hash="hash")
    goal = save_goal(db_session, user.id, goal_request(priority=2))

    assert goal.name == "Emergency fund"
    assert get_goal(db_session, user.id, goal.id).id == goal.id

    updated = save_goal(
        db_session,
        user.id,
        goal_request(name="House deposit", priority=1),
        goal=goal,
    )

    assert updated.id == goal.id
    assert updated.name == "House deposit"
    assert [item.id for item in list_goals(db_session, user.id)] == [goal.id]

    delete_goal(db_session, goal)
    assert get_goal(db_session, user.id, goal.id) is None


def test_save_progress_updates_goal_current_amount_and_rebalances_entries(db_session):
    user = create_user(db_session, email="goal-progress@example.com", password_hash="hash")
    goal = save_goal(db_session, user.id, goal_request())

    first = save_progress(
        db_session,
        goal,
        GoalProgressRequest(
            amount=Decimal("500"),
            progress_date=date(2026, 8, 1),
            note="First transfer",
        ),
    )
    second = save_progress(
        db_session,
        goal,
        GoalProgressRequest(
            amount=Decimal("250"),
            progress_date=date(2026, 8, 15),
        ),
    )

    assert goal.current_amount == Decimal("1750.00")
    assert [item.id for item in list_progress(db_session, goal.id)] == [
        first.id,
        second.id,
    ]
    assert first.new_current_amount == Decimal("1500.00")
    assert second.new_current_amount == Decimal("1750.00")

    delete_progress(db_session, goal, first)
    db_session.refresh(goal)
    db_session.refresh(second)

    assert goal.current_amount == Decimal("1250.00")
    assert second.new_current_amount == Decimal("1250.00")


def test_save_progress_rejects_amount_above_target(db_session):
    user = create_user(db_session, email="goal-over@example.com", password_hash="hash")
    goal = save_goal(db_session, user.id, goal_request())

    with pytest.raises(ValueError, match="Progress would exceed"):
        save_progress(
            db_session,
            goal,
            GoalProgressRequest(
                amount=Decimal("10000"),
                progress_date=date(2026, 8, 1),
            ),
        )


def test_allocation_settings_default_and_update(db_session):
    user = create_user(db_session, email="allocation@example.com", password_hash="hash")

    default_settings = get_allocation_settings(db_session, user.id)
    assert default_settings.cash_allocatable_ratio == Decimal("50.00")
    assert default_settings.monthly_allocatable_ratio == Decimal("50.00")
    assert default_settings.goal_monthly_ratios == []

    updated = save_allocation_settings(
        db_session,
        user.id,
        AllocationSettingsRequest(
            cash_allocatable_ratio=Decimal("40"),
            monthly_allocatable_ratio=Decimal("60"),
            goal_monthly_ratios=[{"goal_id": 1, "ratio": Decimal("25")}],
        ),
    )

    assert updated.id == default_settings.id
    assert updated.cash_allocatable_ratio == Decimal("40.00")
    assert updated.monthly_allocatable_ratio == Decimal("60.00")
    assert updated.goal_monthly_ratios == [{"goal_id": 1, "ratio": "25"}]
