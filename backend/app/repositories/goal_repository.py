from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.goal import Goal, GoalContribution
from app.schemas.goal import GoalRequest


def list_goals(db: Session, user_id: int) -> list[Goal]:
    return db.query(Goal).filter(Goal.user_id == user_id).order_by(Goal.priority, Goal.target_date, Goal.id).all()


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
