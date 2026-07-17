from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


AssetType = Literal["cash", "stocks", "bonds", "property", "vehicle", "others"]
FlowType = Literal["income", "expense"]
DebtType = Literal[
    "mortgage", "car_loan", "personal_loan", "credit_card",
    "student_loan", "bnpl", "tax_debt", "other",
]
Frequency = Literal["weekly", "fortnightly", "monthly", "yearly"]
CashBucketType = Literal["available", "emergency_fund", "home_deposit", "goal_reserved", "debt_reserve", "general_savings", "other"]


class NamedMoneyRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    amount: Decimal = Field(ge=0, max_digits=14, decimal_places=2)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Name must not be blank.")
        return value


class AssetRequest(NamedMoneyRequest):
    asset_type: AssetType


class AssetResponse(AssetRequest):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime
    updated_at: datetime


class CashFlowRequest(NamedMoneyRequest):
    flow_type: FlowType
    date: date


class CashFlowResponse(CashFlowRequest):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime
    updated_at: datetime


class DebtRequest(BaseModel):
    debt_type: DebtType
    name: str = Field(min_length=1, max_length=100)
    balance: Decimal = Field(ge=0, max_digits=14, decimal_places=2)
    minimum_payment: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)
    interest_rate: Decimal | None = Field(default=None, ge=0, le=100, max_digits=7, decimal_places=4)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Name must not be blank.")
        return value


class DebtResponse(DebtRequest):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime
    updated_at: datetime


class RecurringCashFlowRequest(NamedMoneyRequest):
    flow_type: FlowType
    frequency: Frequency
    start_date: date
    end_date: date | None = None
    category: str | None = Field(default=None, max_length=50)

    @field_validator("category")
    @classmethod
    def normalize_category(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None

    @model_validator(mode="after")
    def end_date_not_before_start_date(self):
        if self.end_date is not None and self.end_date < self.start_date:
            raise ValueError("End date must not be before start date.")
        return self


class RecurringCashFlowResponse(RecurringCashFlowRequest):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime
    updated_at: datetime


class CashBucketRequest(BaseModel):
    bucket_type: CashBucketType
    name: str | None = Field(default=None, max_length=100)
    amount: Decimal = Field(default=Decimal("0"), ge=0, max_digits=14, decimal_places=2)

    @field_validator("name")
    @classmethod
    def normalize_optional_name(cls, value: str | None) -> str | None:
        return value.strip() or None if value is not None else None


class CashBucketResponse(CashBucketRequest):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime
    updated_at: datetime


class FinancialsResponse(BaseModel):
    assets: list[AssetResponse]
    debts: list[DebtResponse]
    cash_flows: list[CashFlowResponse]
    recurring_cash_flows: list[RecurringCashFlowResponse]


class AllocationItem(BaseModel):
    asset_type: AssetType
    amount: Decimal


class TrendItem(BaseModel):
    month: str
    amount: Decimal


class DebtBreakdownItem(BaseModel):
    debt_type: DebtType
    amount: Decimal


class FinancialSummaryResponse(BaseModel):
    total_assets: Decimal
    total_debts: Decimal
    net_worth: Decimal
    cash_savings: Decimal
    monthly_income: Decimal
    monthly_expenses: Decimal
    monthly_cash_flow: Decimal
    asset_allocation: list[AllocationItem]
    debt_breakdown: list[DebtBreakdownItem]
    cash_savings_trend: list[TrendItem]
    recent_cash_flows: list[CashFlowResponse]
