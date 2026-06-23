from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.financial_rule import FinancialRule


def get_financial_rule_by_id(
    db: Session,
    rule_id: int,
) -> FinancialRule | None:
    return (
        db.query(FinancialRule)
        .filter(FinancialRule.id == rule_id)
        .first()
    )


def list_financial_rules(
    db: Session,
    region: str | None = None,
    category: str | None = None,
    rule_year: str | None = None,
) -> list[FinancialRule]:
    query = db.query(FinancialRule)

    if region is not None:
        normalized_region = region.strip().lower()

        query = query.filter(
            func.lower(FinancialRule.region)
            == normalized_region
        )

    if category is not None:
        normalized_category = category.strip().lower()

        query = query.filter(
            func.lower(FinancialRule.category)
            == normalized_category
        )

    if rule_year is not None:
        query = query.filter(
            FinancialRule.rule_year
            == rule_year.strip()
        )

    return (
        query
        .order_by(
            FinancialRule.category.asc(),
            FinancialRule.rule_key.asc(),
        )
        .all()
    )