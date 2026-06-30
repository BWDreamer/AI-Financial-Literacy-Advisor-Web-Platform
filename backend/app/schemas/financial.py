from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


AssetType = Literal["cash", "stocks", "bonds", "property", "vehicle", "others"]
FlowType = Literal["income", "expense"]


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


class FinancialsResponse(BaseModel):
    assets: list[AssetResponse]
    cash_flows: list[CashFlowResponse]


class AllocationItem(BaseModel):
    asset_type: AssetType
    amount: Decimal


class TrendItem(BaseModel):
    month: str
    amount: Decimal


class FinancialSummaryResponse(BaseModel):
    net_worth: Decimal
    cash_savings: Decimal
    monthly_income: Decimal
    monthly_expenses: Decimal
    monthly_cash_flow: Decimal
    asset_allocation: list[AllocationItem]
    cash_savings_trend: list[TrendItem]
    recent_cash_flows: list[CashFlowResponse]
