import re
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


GOAL_NAME_PREFIXES = frozenset({"my", "our"})
GOAL_NAME_SUFFIXES = frozenset(
    {"fund", "goal", "goals", "plan", "saving", "savings"}
)
AI_CONFIRMED_GOAL_DETAIL_KEYS = frozenset(
    {"confirmed_monthly_allocation", "confirmed_one_off_allocation"}
)


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


def _canonical_goal_name(name: str) -> str:
    tokens = re.sub(r"[\W_]+", " ", name.casefold()).split()
    while len(tokens) > 1 and tokens[0] in GOAL_NAME_PREFIXES:
        tokens.pop(0)
    while len(tokens) > 1 and tokens[-1] in GOAL_NAME_SUFFIXES:
        tokens.pop()
    return " ".join(tokens)


def _goal_identity(goal: Goal) -> tuple[str, str]:
    return (
        " ".join(goal.category.split()).casefold(),
        _canonical_goal_name(goal.name),
    )


def _is_ai_confirmed_goal(goal: Goal) -> bool:
    return bool(
        AI_CONFIRMED_GOAL_DETAIL_KEYS.intersection(
            (goal.category_details or {}).keys()
        )
    )


def _delete_duplicate_ai_goal(db: Session, goal: Goal) -> None:
    db.query(CashBucket).filter(
        CashBucket.goal_id == goal.id
    ).delete(synchronize_session=False)
    db.query(GoalProgress).filter(
        GoalProgress.goal_id == goal.id
    ).delete(synchronize_session=False)
    db.query(GoalNotification).filter(
        GoalNotification.goal_id == goal.id
    ).delete(synchronize_session=False)
    db.delete(goal)


def _reconcile_confirmed_goals(
    db: Session,
    user_id: int,
    proposed_goals: tuple[Goal, ...],
    proposed_one_off_allocations: tuple[Decimal, ...],
) -> tuple[tuple[Goal, ...], tuple[Decimal, ...], frozenset[int]]:
    """Reuse matching active goals without reducing their saved progress."""
    active_goals = db.query(Goal).filter(
        Goal.user_id == user_id,
        Goal.archived.is_(False),
        Goal.status.notin_(("completed", "pending_archive")),
        Goal.current_amount < Goal.target_amount,
    ).order_by(Goal.id).all()
    active_goals_by_identity: dict[tuple[str, str], list[Goal]] = {}
    for active_goal in active_goals:
        active_goals_by_identity.setdefault(
            _goal_identity(active_goal),
            [],
        ).append(active_goal)
    reconciled_goals: list[Goal] = []
    applied_one_off_allocations: list[Decimal] = []
    removed_duplicate_goal_ids: set[int] = set()

    for proposed_goal, proposed_one_off in zip(
        proposed_goals,
        proposed_one_off_allocations,
        strict=True,
    ):
        matching_goals = active_goals_by_identity.get(
            _goal_identity(proposed_goal),
            [],
        )
        if not matching_goals:
            reconciled_goals.append(proposed_goal)
            applied_one_off_allocations.append(proposed_one_off)
            continue

        existing_goal = matching_goals[0]
        for duplicate_goal in matching_goals[1:]:
            if not _is_ai_confirmed_goal(duplicate_goal):
                continue
            existing_goal.current_amount = max(
                Decimal(existing_goal.current_amount),
                Decimal(duplicate_goal.current_amount),
            )
            removed_duplicate_goal_ids.add(duplicate_goal.id)
            _delete_duplicate_ai_goal(db, duplicate_goal)

        previous_current_amount = Decimal(existing_goal.current_amount)
        reconciled_current_amount = max(
            previous_current_amount,
            Decimal(proposed_goal.current_amount),
        )
        reconciled_target_amount = max(
            Decimal(proposed_goal.target_amount),
            reconciled_current_amount,
        )
        applied_one_off = min(
            proposed_one_off,
            max(
                reconciled_current_amount - previous_current_amount,
                Decimal("0"),
            ),
        )
        category_details = dict(proposed_goal.category_details or {})
        for current_amount_field in ("current_amount", "current_super"):
            if current_amount_field in category_details:
                category_details[current_amount_field] = format(
                    reconciled_current_amount,
                    "f",
                )
        if "confirmed_one_off_allocation" in category_details:
            category_details["confirmed_one_off_allocation"] = format(
                applied_one_off,
                "f",
            )

        existing_goal.target_amount = reconciled_target_amount
        existing_goal.current_amount = reconciled_current_amount
        existing_goal.monthly_contribution = (
            proposed_goal.monthly_contribution
        )
        existing_goal.target_date = proposed_goal.target_date
        existing_goal.priority = proposed_goal.priority
        existing_goal.status = (
            "pending_archive"
            if reconciled_current_amount >= reconciled_target_amount
            else proposed_goal.status
        )
        existing_goal.category_details = category_details
        db.add(existing_goal)
        reconciled_goals.append(existing_goal)
        applied_one_off_allocations.append(applied_one_off)

    return (
        tuple(reconciled_goals),
        tuple(applied_one_off_allocations),
        frozenset(removed_duplicate_goal_ids),
    )


def _sync_confirmed_goal_cash_bucket(
    db: Session,
    user_id: int,
    goal: Goal,
) -> None:
    if goal.current_amount <= 0:
        return
    bucket = db.query(CashBucket).filter(
        CashBucket.user_id == user_id,
        CashBucket.goal_id == goal.id,
        CashBucket.bucket_type == "goal_reserved",
    ).first()
    if bucket is None:
        bucket = CashBucket(
            user_id=user_id,
            goal_id=goal.id,
            bucket_type="goal_reserved",
        )
    bucket.name = goal.name
    bucket.amount = goal.current_amount
    db.add(bucket)


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
        (
            goals,
            one_off_allocations,
            removed_duplicate_goal_ids,
        ) = _reconcile_confirmed_goals(
            db,
            user_id,
            goals,
            one_off_allocations,
        )
        db.add_all(goals)
        db.flush()

        for goal, one_off_amount in zip(
            goals,
            one_off_allocations,
            strict=True,
        ):
            _sync_confirmed_goal_cash_bucket(db, user_id, goal)
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

        has_monthly_ratios = any(ratio > 0 for ratio in monthly_ratios)
        if has_monthly_ratios or removed_duplicate_goal_ids:
            settings = db.query(GoalAllocationSettings).filter(
                GoalAllocationSettings.user_id == user_id
            ).first()
            if settings is None:
                settings = GoalAllocationSettings(
                    user_id=user_id,
                    goal_monthly_ratios=[],
                )
            replaced_goal_ids = {
                goal.id
                for goal in goals
            } | removed_duplicate_goal_ids
            ratio_rows = [
                item
                for item in (settings.goal_monthly_ratios or [])
                if int(item["goal_id"]) not in replaced_goal_ids
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
            if has_monthly_ratios:
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
