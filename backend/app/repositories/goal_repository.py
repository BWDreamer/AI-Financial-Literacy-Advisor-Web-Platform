from datetime import date
from decimal import Decimal

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.financial import CashBucket
from app.models.goal import (
    Goal,
    GoalAllocationSettings,
    GoalNotification,
    GoalPlanConfirmation,
    GoalProgress,
)
from app.schemas.goal import AllocationSettingsRequest, GoalProgressRequest, GoalRequest
from app.services.goal_ratio_service import normalize_goal_ratio_rows


def list_goals(db: Session, user_id: int) -> list[Goal]:
    return db.query(Goal).filter(Goal.user_id == user_id, Goal.archived.is_(False)).order_by(Goal.priority, Goal.target_date, Goal.id).all()


def get_goal(db: Session, user_id: int, goal_id: int) -> Goal | None:
    return db.query(Goal).filter(Goal.id == goal_id, Goal.user_id == user_id).first()


def save_goal(db: Session, user_id: int, data: GoalRequest, goal: Goal | None = None) -> Goal:
    goal = goal or Goal(user_id=user_id)
    for field, value in data.model_dump().items():
        setattr(goal, field, value)
    db.add(goal)
    db.commit()
    db.refresh(goal)
    return goal


def goal_plan_confirmation_exists(
    db: Session,
    conversation_id: int,
    plan_fingerprint: str,
) -> bool:
    return db.query(GoalPlanConfirmation.id).filter(
        GoalPlanConfirmation.conversation_id == conversation_id,
        GoalPlanConfirmation.plan_fingerprint == plan_fingerprint,
    ).first() is not None


def save_confirmed_goal_plan(
    db: Session,
    conversation_id: int,
    plan_fingerprint: str,
    goals: tuple[Goal, ...],
    one_off_allocations: tuple[Decimal, ...],
    monthly_ratios: tuple[Decimal, ...],
) -> bool:
    """Persist one confirmed plan once for its originating conversation."""
    if goal_plan_confirmation_exists(db, conversation_id, plan_fingerprint):
        return False
    if not (
        len(goals)
        == len(one_off_allocations)
        == len(monthly_ratios)
    ):
        raise ValueError("Confirmed goal allocations must align with goals.")
    user_ids = {goal.user_id for goal in goals}
    if len(user_ids) != 1:
        raise ValueError("A confirmed goal plan must belong to one user.")
    user_id = next(iter(user_ids))

    confirmation = GoalPlanConfirmation(
        conversation_id=conversation_id,
        plan_fingerprint=plan_fingerprint,
    )
    try:
        db.add(confirmation)
        db.flush()
        db.add_all(goals)
        db.flush()

        for goal, one_off_amount in zip(
            goals,
            one_off_allocations,
            strict=True,
        ):
            if goal.current_amount > 0:
                db.add(
                    CashBucket(
                        user_id=user_id,
                        goal_id=goal.id,
                        bucket_type="goal_reserved",
                        name=goal.name,
                        amount=goal.current_amount,
                    )
                )
            if one_off_amount > 0:
                db.add(
                    GoalProgress(
                        goal_id=goal.id,
                        amount=one_off_amount,
                        progress_date=date.today(),
                        note="One-off allocation from confirmed AI savings plan",
                        source="ai_plan_one_off",
                        new_current_amount=goal.current_amount,
                    )
                )

        if any(ratio > 0 for ratio in monthly_ratios):
            settings = db.query(GoalAllocationSettings).filter(
                GoalAllocationSettings.user_id == user_id
            ).first()
            if settings is None:
                settings = GoalAllocationSettings(
                    user_id=user_id,
                    goal_monthly_ratios=[],
                )
            new_goal_ids = {goal.id for goal in goals}
            ratio_rows = [
                item
                for item in (settings.goal_monthly_ratios or [])
                if int(item["goal_id"]) not in new_goal_ids
            ]
            ratio_rows.extend(
                {
                    "goal_id": goal.id,
                    "ratio": str(ratio),
                }
                for goal, ratio in zip(
                    goals,
                    monthly_ratios,
                    strict=True,
                )
                if ratio > 0
            )
            settings.monthly_allocatable_ratio = Decimal("100")
            settings.goal_monthly_ratios = normalize_goal_ratio_rows(
                ratio_rows
            )
            db.add(settings)

        db.commit()
    except IntegrityError:
        db.rollback()
        if goal_plan_confirmation_exists(db, conversation_id, plan_fingerprint):
            return False
        raise
    return True


def delete_goal(db: Session, goal: Goal) -> None:
    db.delete(goal)
    db.commit()


def archive_goal(db: Session, goal: Goal) -> Goal:
    goal.status = "completed"
    goal.archived = False
    db.add(goal)
    db.commit()
    db.refresh(goal)
    return goal


def list_progress(db: Session, goal_id: int) -> list[GoalProgress]:
    return db.query(GoalProgress).filter(GoalProgress.goal_id == goal_id).order_by(GoalProgress.progress_date, GoalProgress.id).all()


def get_progress(db: Session, goal_id: int, progress_id: int) -> GoalProgress | None:
    return db.query(GoalProgress).filter(GoalProgress.id == progress_id, GoalProgress.goal_id == goal_id).first()


def save_progress(db: Session, goal: Goal, data: GoalProgressRequest, progress: GoalProgress | None = None) -> GoalProgress:
    old_amount = progress.amount if progress is not None else Decimal("0")
    new_current = goal.current_amount - old_amount + data.amount
    if new_current > goal.target_amount:
        raise ValueError("Progress would exceed the target amount.")
    progress = progress or GoalProgress(goal_id=goal.id)
    for field, value in data.model_dump().items():
        setattr(progress, field, value)
    goal.current_amount = new_current
    progress.new_current_amount = new_current
    db.add_all([goal, progress])
    db.flush()
    _refresh_progress_balances(db, goal)
    db.commit()
    db.refresh(progress)
    return progress


def delete_progress(db: Session, goal: Goal, progress: GoalProgress) -> None:
    goal.current_amount = max(Decimal("0"), goal.current_amount - progress.amount)
    db.delete(progress)
    db.flush()
    _refresh_progress_balances(db, goal)
    db.commit()


def _refresh_progress_balances(db: Session, goal: Goal) -> None:
    entries = list_progress(db, goal.id)
    baseline = goal.current_amount - sum((item.amount for item in entries), Decimal("0"))
    running = baseline
    for item in entries:
        running += item.amount
        item.new_current_amount = running
        db.add(item)


def get_allocation_settings(db: Session, user_id: int) -> GoalAllocationSettings:
    settings = db.query(GoalAllocationSettings).filter(
        GoalAllocationSettings.user_id == user_id
    ).first()
    if settings is not None:
        return settings

    settings = GoalAllocationSettings(
        user_id=user_id,
        goal_monthly_ratios=[],
    )
    db.add(settings)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        settings = db.query(GoalAllocationSettings).filter(
            GoalAllocationSettings.user_id == user_id
        ).first()
        if settings is None:
            raise
        return settings

    db.refresh(settings)
    return settings


def save_allocation_settings(db: Session, user_id: int, data: AllocationSettingsRequest) -> GoalAllocationSettings:
    settings = get_allocation_settings(db, user_id)
    settings.cash_allocatable_ratio = data.cash_allocatable_ratio
    settings.monthly_allocatable_ratio = data.monthly_allocatable_ratio
    settings.goal_monthly_ratios = [item.model_dump(mode="json") for item in data.goal_monthly_ratios]
    db.add(settings)
    db.commit()
    db.refresh(settings)
    return settings


def list_notifications(db: Session, user_id: int) -> list[GoalNotification]:
    return db.query(GoalNotification).filter(
        GoalNotification.user_id == user_id,
        GoalNotification.archived.is_(False),
    ).order_by(GoalNotification.created_at.desc(), GoalNotification.id.desc()).all()


def get_notification(db: Session, user_id: int, notification_id: int) -> GoalNotification | None:
    return db.query(GoalNotification).filter(
        GoalNotification.id == notification_id,
        GoalNotification.user_id == user_id,
    ).first()


def ensure_completion_notification(db: Session, goal: Goal) -> bool:
    if goal.status != "pending_archive":
        return False
    exists = db.query(GoalNotification).filter(
        GoalNotification.goal_id == goal.id,
        GoalNotification.notification_type == "goal_completed",
    ).first()
    if exists is not None:
        return False
    db.add(GoalNotification(
        user_id=goal.user_id,
        goal_id=goal.id,
        notification_type="goal_completed",
        title=f"{goal.name} is ready to archive",
        message="Your goal has reached 100%. Confirm it to move this goal into Completed.",
    ))
    return True
