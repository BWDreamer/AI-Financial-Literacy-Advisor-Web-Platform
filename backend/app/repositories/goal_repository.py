from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.goal import Goal, GoalAllocationSettings, GoalContribution, GoalProgress
from app.schemas.goal import AllocationSettingsRequest, GoalProgressRequest, GoalRequest


def list_goals(db: Session, user_id: int) -> list[Goal]:
    return db.query(Goal).filter(Goal.user_id == user_id).order_by(Goal.priority, Goal.target_date, Goal.id).all()


def get_goal(db: Session, user_id: int, goal_id: int) -> Goal | None:
    return db.query(Goal).filter(Goal.id == goal_id, Goal.user_id == user_id).first()


def save_goal(db: Session, user_id: int, data: GoalRequest, goal: Goal | None = None) -> Goal:
    goal = goal or Goal(user_id=user_id)
    for field, value in data.model_dump(exclude={"status"}).items():
        setattr(goal, field, value)
    if data.status is not None:
        goal.status = data.status
    db.add(goal)
    db.commit()
    db.refresh(goal)
    return goal


def delete_goal(db: Session, goal: Goal) -> None:
    db.delete(goal)
    db.commit()


def add_contribution(db: Session, goal: Goal, amount: Decimal) -> GoalContribution:
    contribution = GoalContribution(goal_id=goal.id, amount=amount)
    goal.current_amount += amount
    db.add_all([goal, contribution])
    db.commit()
    db.refresh(contribution)
    return contribution


def list_contributions(db: Session, goal_id: int) -> list[GoalContribution]:
    return db.query(GoalContribution).filter(GoalContribution.goal_id == goal_id).order_by(GoalContribution.created_at.desc(), GoalContribution.id.desc()).all()


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
    settings = db.query(GoalAllocationSettings).filter(GoalAllocationSettings.user_id == user_id).first()
    if settings is None:
        settings = GoalAllocationSettings(user_id=user_id, goal_monthly_ratios=[])
        db.add(settings)
        db.commit()
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
