from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ProfileUpsertRequest(BaseModel):
    region: str = Field(
        min_length=2,
        max_length=100,
    )

    monthly_income: float = Field(
        ge=0,
        le=9999999999.99,
    )

    fixed_expenses: float = Field(
        ge=0,
        le=9999999999.99,
    )

    current_savings: float = Field(
        ge=0,
        le=9999999999.99,
    )

    initial_savings_target: float = Field(
        ge=0,
        le=9999999999.99,
    )


class ProfileResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True
    )

    id: int
    user_id: int
    region: str
    monthly_income: float
    fixed_expenses: float
    current_savings: float
    initial_savings_target: float
    created_at: datetime