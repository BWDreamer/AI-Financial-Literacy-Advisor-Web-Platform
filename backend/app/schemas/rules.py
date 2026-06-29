from datetime import datetime

from pydantic import BaseModel, ConfigDict


class FinancialRuleResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True
    )

    id: int
    region: str
    category: str
    rule_year: str
    rule_key: str
    rule_value: str
    source_name: str | None
    source_url: str | None
    created_at: datetime


class TaxBracketLookupResponse(BaseModel):
    region: str
    rule_year: str
    taxable_income: float
    bracket: str
    marginal_rate_percent: float
    marginal_rate_label: str
    base_tax: float
    threshold: float
    estimated_tax_excluding_medicare: float
    medicare_levy_included: bool
    formula: str
    source_name: str | None
    source_url: str | None
    llm_context: str


class SuperannuationRuleLookupResponse(BaseModel):
    region: str
    rule_year: str
    period: str
    rate_percent: float
    rate_label: str
    earnings_basis: str
    source_name: str | None
    source_url: str | None
    llm_context: str
