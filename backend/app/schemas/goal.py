from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class GoalRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    category: str = Field(min_length=1, max_length=50)
    target_amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    current_amount: Decimal = Field(default=Decimal("0"), ge=0, max_digits=14, decimal_places=2)
    monthly_contribution: Decimal = Field(default=Decimal("0"), ge=0, max_digits=14, decimal_places=2)
    target_date: date
    priority: int = Field(default=1, ge=1, le=5)

    @field_validator("name", "category")
    @classmethod
    def strip_non_blank_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Value must not be blank.")
        return value

    @model_validator(mode="after")
    def current_amount_not_above_target(self):
        if self.current_amount > self.target_amount:
            raise ValueError("Current amount must not exceed target amount.")
        return self


class GoalResponse(GoalRequest):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime
    updated_at: datetime


class ContributionRequest(BaseModel):
    amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)


class ContributionResponse(ContributionRequest):
    model_config = ConfigDict(from_attributes=True)
    id: int
    goal_id: int
    created_at: datetime


class GoalSummaryResponse(BaseModel):
    total_goals: int
    completed_goals: int
    total_target_amount: Decimal
    total_current_amount: Decimal
    total_monthly_contribution: Decimal
