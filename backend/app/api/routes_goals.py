from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.repositories.goal_repository import add_contribution, delete_goal, get_goal, list_contributions, list_goals, save_goal
from app.schemas.goal import ContributionRequest, ContributionResponse, GoalRequest, GoalResponse, GoalSummaryResponse


router = APIRouter()


@router.get("", response_model=list[GoalResponse])
def get_goals(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return list_goals(db, current_user.id)


@router.post("", response_model=GoalResponse, status_code=status.HTTP_201_CREATED)
def create_goal(request: GoalRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return save_goal(db, current_user.id, request)


@router.get("/summary", response_model=GoalSummaryResponse)
def get_goals_summary(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    goals = list_goals(db, current_user.id)
    return {
        "total_goals": len(goals),
        "completed_goals": sum(goal.current_amount >= goal.target_amount for goal in goals),
        "total_target_amount": sum((goal.target_amount for goal in goals), Decimal("0")),
        "total_current_amount": sum((goal.current_amount for goal in goals), Decimal("0")),
        "total_monthly_contribution": sum((goal.monthly_contribution for goal in goals), Decimal("0")),
    }


def owned_goal_or_404(db: Session, user_id: int, goal_id: int):
    goal = get_goal(db, user_id, goal_id)
    if goal is None:
        raise HTTPException(status_code=404, detail="Goal was not found.")
    return goal


@router.get("/{goal_id}", response_model=GoalResponse)
def get_goal_detail(goal_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return owned_goal_or_404(db, current_user.id, goal_id)


@router.put("/{goal_id}", response_model=GoalResponse)
def update_goal(goal_id: int, request: GoalRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return save_goal(db, current_user.id, request, owned_goal_or_404(db, current_user.id, goal_id))


@router.delete("/{goal_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_goal(goal_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    delete_goal(db, owned_goal_or_404(db, current_user.id, goal_id))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{goal_id}/contributions", response_model=ContributionResponse, status_code=status.HTTP_201_CREATED)
def create_contribution(goal_id: int, request: ContributionRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    goal = owned_goal_or_404(db, current_user.id, goal_id)
    if goal.current_amount + request.amount > goal.target_amount:
        raise HTTPException(status_code=422, detail="Contribution would exceed the target amount.")
    return add_contribution(db, goal, request.amount)


@router.get("/{goal_id}/contributions", response_model=list[ContributionResponse])
def get_contributions(goal_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    goal = owned_goal_or_404(db, current_user.id, goal_id)
    return list_contributions(db, goal.id)
