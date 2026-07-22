from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.repositories.goal_repository import (
    archive_goal, delete_goal, delete_progress, ensure_completion_notification, get_allocation_settings,
    get_goal, get_notification, get_progress, list_goals, list_notifications, list_progress,
    save_allocation_settings, save_goal, save_progress,
)
from app.schemas.goal import (
    AllocationSettingsRequest, AllocationSettingsResponse,
    GoalAnalysisResponse, GoalChartResponse, GoalNotificationResponse, GoalPreviewRequest, GoalPreviewResponse,
    GoalProgressRequest, GoalProgressResponse, GoalRequest, GoalResponse, GoalSummaryResponse,
)
from app.services.goal_service import (
    active_goal_ratios, analyse_goal, apply_due_monthly_progress, backfill_goal_ratios, build_goal_chart, build_goal_preview, calculate_monthly_allocation,
    financial_numbers, linked_cash_allocation, money, monthly_allocation_map,
    refresh_goal_status, sync_goal_monthly_ratio, sync_goal_reserved_cash, validate_owned_ratios,
)

router = APIRouter()


def owned_goal_or_404(db: Session, user_id: int, goal_id: int):
    goal = get_goal(db, user_id, goal_id)
    if goal is None:
        raise HTTPException(status_code=404, detail="Goal was not found.")
    return goal


def goal_response(goal, allocated_monthly: Decimal | None = None, cash_allocation: Decimal | None = None) -> dict:
    analysis = analyse_goal(goal, allocated_monthly=allocated_monthly, cash_allocation=cash_allocation)
    return {
        "id": goal.id, "name": goal.name, "category": goal.category,
        "target_amount": goal.target_amount, "current_amount": goal.current_amount,
        "monthly_contribution": goal.monthly_contribution, "target_date": goal.target_date,
        "priority": goal.priority, "status": goal.status,
        "category_details": goal.category_details or {}, "created_at": goal.created_at,
        "updated_at": goal.updated_at, "archived": goal.archived,
        "allocated_monthly": analysis["allocated_monthly"],
        "cash_allocation": analysis["cash_allocation"],
        "progress_percentage": analysis["progress_percentage"],
    }


def settings_response(db: Session, user_id: int, settings) -> dict:
    goals = list_goals(db, user_id)
    finance = financial_numbers(db, user_id)
    if backfill_goal_ratios(goals, finance, settings):
        db.add(settings); db.commit(); db.refresh(settings)
    monthly = calculate_monthly_allocation(
        finance, Decimal(settings.monthly_allocatable_ratio),
        active_goal_ratios(goals, settings.goal_monthly_ratios or []),
    )
    return {
        "cash_allocatable_ratio": settings.cash_allocatable_ratio,
        "monthly_allocatable_ratio": settings.monthly_allocatable_ratio,
        "goal_monthly_ratios": active_goal_ratios(goals, settings.goal_monthly_ratios or []),
        "monthly_allocation": monthly,
    }


def sync_goal_state(db: Session, goals: list, monthly_map: dict[int, Decimal]) -> None:
    changed = apply_due_monthly_progress(db, goals, monthly_map)
    for goal in goals:
        cash = linked_cash_allocation(db, goal)
        status_value = analyse_goal(goal, allocated_monthly=monthly_map.get(goal.id), cash_allocation=cash)["status"]
        if goal.status != status_value:
            goal.status = status_value
            changed = True
        if sync_goal_reserved_cash(db, goal):
            changed = True
        if ensure_completion_notification(db, goal):
            changed = True
        db.add(goal)
    if changed:
        db.commit()


@router.get("", response_model=list[GoalResponse])
def get_goals(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    goals = list_goals(db, current_user.id)
    settings = get_allocation_settings(db, current_user.id)
    finance = financial_numbers(db, current_user.id)
    if backfill_goal_ratios(goals, finance, settings):
        db.add(settings); db.commit(); db.refresh(settings)
    monthly_map = monthly_allocation_map(db, current_user.id, settings)
    sync_goal_state(db, goals, monthly_map)
    return [goal_response(goal, monthly_map.get(goal.id), linked_cash_allocation(db, goal)) for goal in goals]


@router.post("", response_model=GoalResponse, status_code=status.HTTP_201_CREATED)
def create_goal(request: GoalRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    goal = save_goal(db, current_user.id, request)
    sync_goal_monthly_ratio(db, goal)
    refresh_goal_status(goal)
    sync_goal_reserved_cash(db, goal)
    ensure_completion_notification(db, goal)
    db.add(goal); db.commit(); db.refresh(goal)
    return goal_response(goal, cash_allocation=linked_cash_allocation(db, goal))


@router.post("/preview", response_model=GoalPreviewResponse, response_model_exclude_none=True)
def preview_goal(request: GoalPreviewRequest, current_user: User = Depends(get_current_user)):
    try:
        return build_goal_preview(request)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/allocation-settings", response_model=AllocationSettingsResponse)
def read_allocation_settings(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return settings_response(db, current_user.id, get_allocation_settings(db, current_user.id))


@router.put("/allocation-settings", response_model=AllocationSettingsResponse)
def update_allocation_settings(request: AllocationSettingsRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    goals = list_goals(db, current_user.id)
    try:
        validate_owned_ratios(goals, request.goal_monthly_ratios)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    request = request.model_copy(update={"goal_monthly_ratios": active_goal_ratios(goals, request.goal_monthly_ratios)})
    settings = save_allocation_settings(db, current_user.id, request)
    return settings_response(db, current_user.id, settings)


@router.get("/summary", response_model=GoalSummaryResponse)
def get_goals_summary(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    goals = list_goals(db, current_user.id)
    settings = get_allocation_settings(db, current_user.id)
    finance = financial_numbers(db, current_user.id)
    if backfill_goal_ratios(goals, finance, settings):
        db.add(settings); db.commit(); db.refresh(settings)
    monthly = calculate_monthly_allocation(finance, Decimal(settings.monthly_allocatable_ratio), active_goal_ratios(goals, settings.goal_monthly_ratios or []))
    monthly_map = {int(row["goal_id"]): Decimal(row["monthly_amount"]) for row in monthly["goals"]}
    sync_goal_state(db, goals, monthly_map)
    finance = financial_numbers(db, current_user.id)
    monthly = calculate_monthly_allocation(finance, Decimal(settings.monthly_allocatable_ratio), active_goal_ratios(goals, settings.goal_monthly_ratios or []))
    monthly_map = {int(row["goal_id"]): Decimal(row["monthly_amount"]) for row in monthly["goals"]}
    cash_by_goal = {goal.id: linked_cash_allocation(db, goal) for goal in goals}
    analyses = [analyse_goal(goal, allocated_monthly=monthly_map.get(goal.id), cash_allocation=cash_by_goal[goal.id]) for goal in goals]
    cash_savings = money(Decimal(finance["cash_savings"]))
    cash_allocatable = money(max(cash_savings, Decimal("0")) * Decimal(settings.cash_allocatable_ratio) / 100)
    cash_already_assigned = money(sum(cash_by_goal.values(), Decimal("0")))
    return {
        "total_goals": len(goals), "on_track_goals": sum(item["status"] == "on_track" for item in analyses),
        "behind_goals": sum(item["status"] == "behind" for item in analyses), "completed_goals": sum(goal.status == "completed" for goal in goals),
        "cash_savings": cash_savings, "cash_allocatable": cash_allocatable,
        "cash_already_assigned": cash_already_assigned,
        "cash_unassigned": money(max(cash_allocatable - cash_already_assigned, Decimal("0"))),
        "monthly_net_income": monthly["monthly_net_income"], "monthly_allocatable": monthly["monthly_allocatable"],
        "monthly_already_assigned": monthly["already_assigned"],
        "monthly_unassigned": monthly["unassigned"],
        "total_target_amount": sum((goal.target_amount for goal in goals), Decimal("0")),
        "total_current_amount": sum((goal.current_amount for goal in goals), Decimal("0")),
        "total_monthly_contribution": sum((goal.monthly_contribution for goal in goals), Decimal("0")),
    }


@router.get("/notifications", response_model=list[GoalNotificationResponse])
def get_goal_notifications(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    goals = list_goals(db, current_user.id)
    settings = get_allocation_settings(db, current_user.id)
    sync_goal_state(db, goals, monthly_allocation_map(db, current_user.id, settings))
    return list_notifications(db, current_user.id)


@router.post("/notifications/{notification_id}/read", response_model=GoalNotificationResponse)
def read_goal_notification(notification_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    notification = get_notification(db, current_user.id, notification_id)
    if notification is None:
        raise HTTPException(status_code=404, detail="Goal notification was not found.")
    notification.read = True
    db.add(notification); db.commit(); db.refresh(notification)
    return notification


@router.post("/{goal_id}/archive", response_model=GoalResponse)
def archive_completed_goal(goal_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    goal = owned_goal_or_404(db, current_user.id, goal_id)
    if goal.status != "pending_archive":
        raise HTTPException(status_code=422, detail="Only pending archive goals can be confirmed.")
    goal = archive_goal(db, goal)
    sync_goal_reserved_cash(db, goal)
    for notification in list_notifications(db, current_user.id):
        if notification.goal_id == goal.id:
            notification.read = True; notification.archived = True; db.add(notification)
    db.commit()
    return goal_response(goal)


@router.get("/{goal_id}", response_model=GoalResponse)
def get_goal_detail(goal_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    goal = owned_goal_or_404(db, current_user.id, goal_id)
    settings = get_allocation_settings(db, current_user.id)
    monthly_map = monthly_allocation_map(db, current_user.id, settings)
    sync_goal_state(db, [goal], monthly_map)
    db.refresh(goal)
    return goal_response(goal, monthly_map.get(goal.id), linked_cash_allocation(db, goal))


@router.put("/{goal_id}", response_model=GoalResponse)
def update_goal(goal_id: int, request: GoalRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    existing = owned_goal_or_404(db, current_user.id, goal_id)
    if existing.status == "completed":
        raise HTTPException(status_code=422, detail="Completed goals cannot be edited.")
    goal = save_goal(db, current_user.id, request, existing)
    sync_goal_monthly_ratio(db, goal)
    sync_goal_reserved_cash(db, goal)
    settings = get_allocation_settings(db, current_user.id)
    monthly_map = monthly_allocation_map(db, current_user.id, settings)
    goal.status = analyse_goal(goal, allocated_monthly=monthly_map.get(goal.id), cash_allocation=linked_cash_allocation(db, goal))["status"]
    ensure_completion_notification(db, goal)
    db.add(goal); db.commit(); db.refresh(goal)
    return goal_response(goal, monthly_map.get(goal.id), linked_cash_allocation(db, goal))


@router.delete("/{goal_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_goal(goal_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    delete_goal(db, owned_goal_or_404(db, current_user.id, goal_id))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{goal_id}/analysis", response_model=GoalAnalysisResponse)
def get_goal_analysis(goal_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    goal = owned_goal_or_404(db, current_user.id, goal_id)
    settings = get_allocation_settings(db, current_user.id)
    monthly_map = monthly_allocation_map(db, current_user.id, settings)
    sync_goal_state(db, [goal], monthly_map)
    db.refresh(goal)
    return analyse_goal(goal, allocated_monthly=monthly_map.get(goal.id), cash_allocation=linked_cash_allocation(db, goal))


@router.get("/{goal_id}/chart", response_model=GoalChartResponse)
def get_goal_chart(goal_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    goal = owned_goal_or_404(db, current_user.id, goal_id)
    settings = get_allocation_settings(db, current_user.id)
    sync_goal_state(db, [goal], monthly_allocation_map(db, current_user.id, settings))
    db.refresh(goal)
    return build_goal_chart(db, goal)


@router.get("/{goal_id}/progress", response_model=list[GoalProgressResponse])
def get_goal_progress(goal_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    goal = owned_goal_or_404(db, current_user.id, goal_id)
    return list_progress(db, goal.id)


@router.post("/{goal_id}/progress", response_model=GoalProgressResponse, status_code=status.HTTP_201_CREATED)
def create_goal_progress(goal_id: int, request: GoalProgressRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    goal = owned_goal_or_404(db, current_user.id, goal_id)
    if goal.status == "completed":
        raise HTTPException(status_code=422, detail="Completed goals cannot be changed.")
    try:
        result = save_progress(db, goal, request)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    sync_goal_reserved_cash(db, goal); refresh_goal_status(goal); ensure_completion_notification(db, goal); db.add(goal); db.commit()
    return result


@router.put("/{goal_id}/progress/{progress_id}", response_model=GoalProgressResponse)
def update_goal_progress(goal_id: int, progress_id: int, request: GoalProgressRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    goal = owned_goal_or_404(db, current_user.id, goal_id)
    if goal.status == "completed":
        raise HTTPException(status_code=422, detail="Completed goals cannot be changed.")
    progress = get_progress(db, goal.id, progress_id)
    if progress is None:
        raise HTTPException(status_code=404, detail="Goal progress was not found.")
    try:
        result = save_progress(db, goal, request, progress)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    sync_goal_reserved_cash(db, goal); refresh_goal_status(goal); ensure_completion_notification(db, goal); db.add(goal); db.commit()
    return result


@router.delete("/{goal_id}/progress/{progress_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_goal_progress(goal_id: int, progress_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    goal = owned_goal_or_404(db, current_user.id, goal_id)
    if goal.status == "completed":
        raise HTTPException(status_code=422, detail="Completed goals cannot be changed.")
    progress = get_progress(db, goal.id, progress_id)
    if progress is None:
        raise HTTPException(status_code=404, detail="Goal progress was not found.")
    delete_progress(db, goal, progress); sync_goal_reserved_cash(db, goal); refresh_goal_status(goal); db.add(goal); db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
