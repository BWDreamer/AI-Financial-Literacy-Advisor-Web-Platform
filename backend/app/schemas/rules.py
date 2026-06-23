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