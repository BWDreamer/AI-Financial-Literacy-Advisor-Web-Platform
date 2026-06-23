from fastapi import APIRouter, Query

from app.schemas.calculator import (
    CompoundInterestRequest,
    CompoundInterestResponse,
    GoalMonthlySavingRequest,
    GoalMonthlySavingResponse,
)
from app.services.calculator_service import (
    calculate_compound_interest,
    calculate_goal_monthly_saving,
)


router = APIRouter()


@router.get("/ping")
def ping_calculator():
    return {
        "module": "calculator",
        "status": "ok",
    }


@router.post(
    "/compound-interest",
    response_model=CompoundInterestResponse,
)
def compound_interest(
    request: CompoundInterestRequest,
):
    return calculate_compound_interest(
        principal=request.principal,
        annual_interest_rate=(
            request.annual_interest_rate
        ),
        years=request.years,
        compounds_per_year=(
            request.compounds_per_year
        ),
    )


@router.post(
    "/goal-monthly-saving",
    response_model=GoalMonthlySavingResponse,
)
def goal_monthly_saving(
    request: GoalMonthlySavingRequest,
):
    return calculate_goal_monthly_saving(
        target_amount=request.target_amount,
        current_amount=request.current_amount,
        months=request.months,
        annual_interest_rate=(
            request.annual_interest_rate
        ),
    )


@router.get(
    "/goal-monthly-saving",
    response_model=GoalMonthlySavingResponse,
)
def legacy_goal_monthly_saving(
    target_amount: float = Query(
        gt=0,
    ),
    current_amount: float = Query(
        ge=0,
    ),
    months: int = Query(
        gt=0,
    ),
    annual_interest_rate: float = Query(
        default=0,
        ge=0,
        le=50,
    ),
):
    return calculate_goal_monthly_saving(
        target_amount=target_amount,
        current_amount=current_amount,
        months=months,
        annual_interest_rate=(
            annual_interest_rate
        ),
    )