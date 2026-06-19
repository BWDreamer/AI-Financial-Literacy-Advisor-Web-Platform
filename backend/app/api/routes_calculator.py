from fastapi import APIRouter
from app.services.calculator_service import calculate_goal_monthly_saving

router = APIRouter()

@router.get("/ping")
def ping_calculator():
    return {"module": "calculator", "status": "ok"}

@router.get("/goal-monthly-saving")
def goal_monthly_saving(target_amount: float, current_amount: float, months: int):
    return calculate_goal_monthly_saving(target_amount, current_amount, months)
