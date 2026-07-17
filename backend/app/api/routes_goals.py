from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.repositories.goal_repository import (
    add_contribution, delete_goal, delete_progress, get_allocation_settings, get_goal, get_progress,
    list_contributions, list_goals, list_progress, save_allocation_settings, save_goal, save_progress,
)
from app.schemas.goal import (
    AllocationSettingsRequest, AllocationSettingsResponse, ContributionRequest, ContributionResponse,
    GoalAnalysisResponse, GoalChartResponse, GoalProgressRequest, GoalProgressResponse, GoalRequest,
    GoalResponse, GoalSummaryResponse, MonthlyAllocationRequest, MonthlyAllocationResponse,
)
from app.services.goal_service import (
    analyse_goal, build_goal_chart, calculate_monthly_allocation, financial_numbers, money,
    refresh_goal_status, validate_owned_ratios,
)

router = APIRouter()


def owned_goal_or_404(db: Session, user_id: int, goal_id: int):
    goal = get_goal(db, user_id, goal_id)
    if goal is None:
        raise HTTPException(status_code=404, detail="Goal was not found.")
    return goal


def settings_response(settings) -> dict:
    return {
        "cash_allocatable_ratio": settings.cash_allocatable_ratio,
        "monthly_allocatable_ratio": settings.monthly_allocatable_ratio,
        "goal_monthly_ratios": settings.goal_monthly_ratios or [],
    }


@router.get("", response_model=list[GoalResponse])
def get_goals(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    goals = list_goals(db, current_user.id)
    changed = False
    for goal in goals:
        calculated = analyse_goal(goal)["status"]
        if goal.status != calculated:
            goal.status = calculated
            db.add(goal)
            changed = True
    if changed:
        db.commit()
    return goals


@router.post("", response_model=GoalResponse, status_code=status.HTTP_201_CREATED)
def create_goal(request: GoalRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    goal = save_goal(db, current_user.id, request)
    refresh_goal_status(goal)
    db.add(goal); db.commit(); db.refresh(goal)
    return goal


@router.get("/allocation-settings", response_model=AllocationSettingsResponse)
def read_allocation_settings(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return settings_response(get_allocation_settings(db, current_user.id))


@router.put("/allocation-settings", response_model=AllocationSettingsResponse)
def update_allocation_settings(request: AllocationSettingsRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        validate_owned_ratios(list_goals(db, current_user.id), request.goal_monthly_ratios)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return settings_response(save_allocation_settings(db, current_user.id, request))


@router.put("/monthly-allocation", response_model=MonthlyAllocationResponse)
def update_monthly_allocation(request: MonthlyAllocationRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    goals = list_goals(db, current_user.id)
    try:
        validate_owned_ratios(goals, request.goal_monthly_ratios)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    settings = get_allocation_settings(db, current_user.id)
    settings_request = AllocationSettingsRequest(
        cash_allocatable_ratio=settings.cash_allocatable_ratio,
        monthly_allocatable_ratio=request.monthly_allocatable_ratio,
        goal_monthly_ratios=request.goal_monthly_ratios,
    )
    save_allocation_settings(db, current_user.id, settings_request)
    result = calculate_monthly_allocation(financial_numbers(db, current_user.id), request.monthly_allocatable_ratio, request.goal_monthly_ratios)
    amounts = {item["goal_id"]: item["monthly_amount"] for item in result["goals"]}
    for goal in goals:
        goal.monthly_contribution = amounts.get(goal.id, Decimal("0"))
        refresh_goal_status(goal)
        db.add(goal)
    db.commit()
    return result


@router.get("/summary", response_model=GoalSummaryResponse)
def get_goals_summary(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    goals = list_goals(db, current_user.id)
    analyses = [analyse_goal(goal) for goal in goals]
    settings = get_allocation_settings(db, current_user.id)
    finance = financial_numbers(db, current_user.id)
    monthly = calculate_monthly_allocation(finance, Decimal(settings.monthly_allocatable_ratio), [type("Ratio", (), item) for item in (settings.goal_monthly_ratios or [])])
    cash_savings = money(Decimal(finance["cash_savings"]))
    cash_allocatable = money(max(cash_savings, Decimal("0")) * Decimal(settings.cash_allocatable_ratio) / 100)
    assigned_ratio = sum((Decimal(str(item["ratio"])) for item in (settings.goal_monthly_ratios or [])), Decimal("0"))
    return {
        "total_goals": len(goals), "on_track_goals": sum(item["status"] == "on_track" for item in analyses),
        "behind_goals": sum(item["status"] == "behind" for item in analyses), "completed_goals": sum(item["status"] == "completed" for item in analyses),
        "cash_savings": cash_savings, "cash_allocatable": cash_allocatable,
        "cash_already_assigned": money(cash_allocatable * min(assigned_ratio, Decimal("100")) / 100),
        "monthly_net_income": monthly["monthly_net_income"], "monthly_allocatable": monthly["monthly_allocatable"],
        "monthly_already_assigned": monthly["already_assigned"],
        "total_target_amount": sum((goal.target_amount for goal in goals), Decimal("0")),
        "total_current_amount": sum((goal.current_amount for goal in goals), Decimal("0")),
        "total_monthly_contribution": sum((goal.monthly_contribution for goal in goals), Decimal("0")),
    }


@router.get("/{goal_id}", response_model=GoalResponse)
def get_goal_detail(goal_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    goal = owned_goal_or_404(db, current_user.id, goal_id)
    refresh_goal_status(goal); db.add(goal); db.commit(); db.refresh(goal)
    return goal


@router.put("/{goal_id}", response_model=GoalResponse)
def update_goal(goal_id: int, request: GoalRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    goal = save_goal(db, current_user.id, request, owned_goal_or_404(db, current_user.id, goal_id))
    refresh_goal_status(goal); db.add(goal); db.commit(); db.refresh(goal)
    return goal


@router.delete("/{goal_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_goal(goal_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    delete_goal(db, owned_goal_or_404(db, current_user.id, goal_id))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{goal_id}/analysis", response_model=GoalAnalysisResponse)
def get_goal_analysis(goal_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return analyse_goal(owned_goal_or_404(db, current_user.id, goal_id))


@router.get("/{goal_id}/chart", response_model=GoalChartResponse)
def get_goal_chart(goal_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return build_goal_chart(db, owned_goal_or_404(db, current_user.id, goal_id))


@router.get("/{goal_id}/progress", response_model=list[GoalProgressResponse])
def get_goal_progress(goal_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    goal = owned_goal_or_404(db, current_user.id, goal_id)
    return list_progress(db, goal.id)


@router.post("/{goal_id}/progress", response_model=GoalProgressResponse, status_code=status.HTTP_201_CREATED)
def create_goal_progress(goal_id: int, request: GoalProgressRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    goal = owned_goal_or_404(db, current_user.id, goal_id)
    try:
        result = save_progress(db, goal, request)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    refresh_goal_status(goal); db.add(goal); db.commit()
    return result


@router.put("/{goal_id}/progress/{progress_id}", response_model=GoalProgressResponse)
def update_goal_progress(goal_id: int, progress_id: int, request: GoalProgressRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    goal = owned_goal_or_404(db, current_user.id, goal_id)
    progress = get_progress(db, goal.id, progress_id)
    if progress is None:
        raise HTTPException(status_code=404, detail="Goal progress was not found.")
    try:
        result = save_progress(db, goal, request, progress)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    refresh_goal_status(goal); db.add(goal); db.commit()
    return result


@router.delete("/{goal_id}/progress/{progress_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_goal_progress(goal_id: int, progress_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    goal = owned_goal_or_404(db, current_user.id, goal_id)
    progress = get_progress(db, goal.id, progress_id)
    if progress is None:
        raise HTTPException(status_code=404, detail="Goal progress was not found.")
    delete_progress(db, goal, progress); refresh_goal_status(goal); db.add(goal); db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{goal_id}/contributions", response_model=ContributionResponse, status_code=status.HTTP_201_CREATED)
def create_contribution(goal_id: int, request: ContributionRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    goal = owned_goal_or_404(db, current_user.id, goal_id)
    if goal.current_amount + request.amount > goal.target_amount:
        raise HTTPException(status_code=422, detail="Contribution would exceed the target amount.")
    result = add_contribution(db, goal, request.amount); refresh_goal_status(goal); db.add(goal); db.commit()
    return result


@router.get("/{goal_id}/contributions", response_model=list[ContributionResponse])
def get_contributions(goal_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    goal = owned_goal_or_404(db, current_user.id, goal_id)
    return list_contributions(db, goal.id)
