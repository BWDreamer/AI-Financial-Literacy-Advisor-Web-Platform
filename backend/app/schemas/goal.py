from datetime import date, datetime
from decimal import Decimal

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

GoalStatus = Literal["on_track", "behind", "pending_archive", "completed"]


class GoalRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    category: str = Field(min_length=1, max_length=50)
    target_amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    current_amount: Decimal = Field(default=Decimal("0"), ge=0, max_digits=14, decimal_places=2)
    monthly_contribution: Decimal = Field(default=Decimal("0"), ge=0, max_digits=14, decimal_places=2)
    target_date: date
    priority: int = Field(default=1, ge=1, le=5)
    category_details: dict[str, Any] = Field(default_factory=dict)

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


class GoalPreviewRequest(BaseModel):
    category: str = Field(min_length=1, max_length=50)
    target_date: date
    priority: Literal["High", "Medium", "Low"] = "Medium"
    category_details: dict[str, Any] = Field(default_factory=dict)


class GoalResponse(GoalRequest):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime
    updated_at: datetime
    status: GoalStatus
    progress_percentage: Decimal
    allocated_monthly: Decimal = Decimal("0")
    cash_allocation: Decimal = Decimal("0")
    archived: bool = False


class GoalSummaryResponse(BaseModel):
    total_goals: int
    on_track_goals: int
    behind_goals: int
    completed_goals: int
    cash_savings: Decimal
    cash_allocatable: Decimal
    cash_already_assigned: Decimal
    cash_unassigned: Decimal
    monthly_net_income: Decimal
    monthly_allocatable: Decimal
    monthly_already_assigned: Decimal
    monthly_unassigned: Decimal
    total_target_amount: Decimal
    total_current_amount: Decimal
    total_monthly_contribution: Decimal


class GoalAnalysisResponse(BaseModel):
    progress_percentage: Decimal
    required_monthly: Decimal
    monthly_difference: Decimal
    allocated_monthly: Decimal
    cash_allocation: Decimal
    months_remaining: int
    projected_completion_date: date | None
    status: GoalStatus


class GoalPreviewResponse(BaseModel):
    goal: GoalRequest
    analysis: GoalAnalysisResponse


class GoalProgressRequest(BaseModel):
    amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    progress_date: date
    note: str | None = Field(default=None, max_length=1000)
    source: str = Field(default="manual", min_length=1, max_length=50)


class GoalProgressResponse(GoalProgressRequest):
    model_config = ConfigDict(from_attributes=True)
    id: int
    goal_id: int
    new_current_amount: Decimal
    created_at: datetime
    updated_at: datetime


class ChartPoint(BaseModel):
    date: date
    amount: Decimal


class GoalChartResponse(BaseModel):
    actual_progress_points: list[ChartPoint]
    expected_progress_points: list[ChartPoint]
    target_amount: Decimal


class GoalRatio(BaseModel):
    goal_id: int
    ratio: Decimal = Field(ge=0, le=100, max_digits=5, decimal_places=2)


class AllocationSettingsRequest(BaseModel):
    cash_allocatable_ratio: Decimal = Field(ge=0, le=100, max_digits=5, decimal_places=2)
    monthly_allocatable_ratio: Decimal = Field(ge=0, le=100, max_digits=5, decimal_places=2)
    goal_monthly_ratios: list[GoalRatio] = Field(default_factory=list)

    @model_validator(mode="after")
    def ratios_must_be_unique_and_not_exceed_100(self):
        ids = [item.goal_id for item in self.goal_monthly_ratios]
        if len(ids) != len(set(ids)):
            raise ValueError("Each goal may only appear once.")
        if sum((item.ratio for item in self.goal_monthly_ratios), Decimal("0")) > 100:
            raise ValueError("Total goal monthly ratio must be at most 100%.")
        return self


class GoalMonthlyAmount(BaseModel):
    goal_id: int
    ratio: Decimal
    monthly_amount: Decimal


class GoalNotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    goal_id: int
    notification_type: str
    title: str
    message: str
    read: bool
    archived: bool
    created_at: datetime
    updated_at: datetime


class MonthlyAllocationResponse(BaseModel):
    monthly_net_income: Decimal
    monthly_allocatable: Decimal
    already_assigned: Decimal
    unassigned: Decimal
    goals: list[GoalMonthlyAmount]


class AllocationSettingsResponse(AllocationSettingsRequest):
    monthly_allocation: MonthlyAllocationResponse
