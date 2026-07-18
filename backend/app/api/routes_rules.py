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
from app.schemas.rules import (
    FinancialRuleResponse,
    SuperannuationRuleLookupResponse,
    TaxBracketLookupResponse,
)
from app.services.rule_lookup_service import (
    lookup_employer_superannuation_rule,
    lookup_tax_bracket,
)


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
    "/tax-bracket",
    response_model=TaxBracketLookupResponse,
)
def get_tax_bracket(
    income: float = Query(
        ge=0,
        le=1_000_000_000_000,
    ),
    region: str = Query(
        default="Australia",
        min_length=1,
        max_length=100,
    ),
    rule_year: str = Query(
        default="2026-2027",
        min_length=1,
        max_length=20,
    ),
    db: Session = Depends(get_db),
):
    """Return the Australian resident tax bracket for a taxable income."""
    result = lookup_tax_bracket(
        db=db,
        region=region,
        rule_year=rule_year,
        income=income,
    )

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                "No tax bracket rule was found for the "
                "requested region and year."
            ),
        )

    return result


@router.get(
    "/superannuation/employer-contribution",
    response_model=SuperannuationRuleLookupResponse,
)
def get_employer_superannuation_rule(
    region: str = Query(
        default="Australia",
        min_length=1,
        max_length=100,
    ),
    rule_year: str = Query(
        default="2026-2027",
        min_length=1,
        max_length=20,
    ),
    db: Session = Depends(get_db),
):
    """Return the employer super guarantee rule for a year."""
    result = lookup_employer_superannuation_rule(
        db=db,
        region=region,
        rule_year=rule_year,
    )

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                "No employer superannuation rule was found "
                "for the requested region and year."
            ),
        )

    return result


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
