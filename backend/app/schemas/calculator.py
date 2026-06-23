from pydantic import BaseModel, ConfigDict, Field


class CompoundInterestRequest(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)

    principal: float = Field(
        ge=0,
        le=1_000_000_000_000,
        description="Initial principal amount.",
    )
    annual_interest_rate: float = Field(
        ge=0,
        le=50,
        description="Annual interest rate as a percentage. For example, 5 means 5%.",
    )
    years: float = Field(
        gt=0,
        le=80,
        description="Investment period in years.",
    )
    compounds_per_year: int = Field(
        default=12,
        ge=1,
        le=365,
        description="Number of compounding periods per year.",
    )


class CompoundInterestResponse(BaseModel):
    principal: float
    annual_interest_rate: float
    years: float
    compounds_per_year: int
    final_amount: float
    interest_earned: float


class GoalMonthlySavingRequest(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)

    target_amount: float = Field(
        gt=0,
        le=1_000_000_000_000,
    )
    current_amount: float = Field(
        ge=0,
        le=1_000_000_000_000,
    )
    months: int = Field(
        gt=0,
        le=1200,
    )
    annual_interest_rate: float = Field(
        default=0,
        ge=0,
        le=50,
        description="Expected annual interest rate as a percentage.",
    )


class GoalMonthlySavingResponse(BaseModel):
    target_amount: float
    current_amount: float
    months: int
    annual_interest_rate: float
    projected_current_amount: float
    remaining_amount: float
    required_monthly_saving: float
    additional_saving_required: bool