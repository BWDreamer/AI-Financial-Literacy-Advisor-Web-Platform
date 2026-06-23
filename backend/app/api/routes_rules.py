from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    status,
)
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.repositories.rule_repository import (
    get_financial_rule_by_id,
    list_financial_rules,
)
from app.schemas.rules import FinancialRuleResponse


router = APIRouter()


@router.get("/ping")
def ping_rules():
    return {
        "module": "rules",
        "status": "ok",
    }


@router.get(
    "",
    response_model=list[FinancialRuleResponse],
)
def get_financial_rules(
    region: str | None = Query(
        default=None,
        min_length=1,
        max_length=100,
    ),
    category: str | None = Query(
        default=None,
        min_length=1,
        max_length=100,
    ),
    rule_year: str | None = Query(
        default=None,
        min_length=1,
        max_length=20,
    ),
    db: Session = Depends(get_db),
):
    return list_financial_rules(
        db=db,
        region=region,
        category=category,
        rule_year=rule_year,
    )


@router.get(
    "/{rule_id}",
    response_model=FinancialRuleResponse,
)
def get_financial_rule(
    rule_id: int,
    db: Session = Depends(get_db),
):
    rule = get_financial_rule_by_id(
        db,
        rule_id,
    )

    if rule is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Financial rule was not found.",
        )

    return rule