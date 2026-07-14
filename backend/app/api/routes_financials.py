from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.repositories.financial_repository import (
    delete_asset,
    delete_cash_flow,
    delete_debt,
    delete_recurring_cash_flow,
    get_asset,
    get_cash_flow,
    get_debt,
    get_recurring_cash_flow,
    list_assets,
    list_cash_flows,
    list_debts,
    list_recurring_cash_flows,
    save_asset,
    save_cash_flow,
    save_debt,
    save_recurring_cash_flow,
)
from app.schemas.financial import (
    AssetRequest,
    AssetResponse,
    CashFlowRequest,
    CashFlowResponse,
    DebtRequest,
    DebtResponse,
    FinancialsResponse,
    FinancialSummaryResponse,
    RecurringCashFlowRequest,
    RecurringCashFlowResponse,
)
from app.services.financial_service import build_financial_summary


router = APIRouter()


@router.get("", response_model=FinancialsResponse)
def get_financials(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return {
        "assets": list_assets(db, current_user.id),
        "debts": list_debts(db, current_user.id),
        "cash_flows": list_cash_flows(db, current_user.id),
        "recurring_cash_flows": list_recurring_cash_flows(db, current_user.id),
    }


@router.get("/summary", response_model=FinancialSummaryResponse)
def get_financial_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return build_financial_summary(
        list_assets(db, current_user.id),
        list_debts(db, current_user.id),
        list_cash_flows(db, current_user.id),
        list_recurring_cash_flows(db, current_user.id),
    )


@router.post("/assets", response_model=AssetResponse, status_code=status.HTTP_201_CREATED)
def create_asset(
    request: AssetRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return save_asset(db, current_user.id, request)


@router.put("/assets/{asset_id}", response_model=AssetResponse)
def update_asset(
    asset_id: int,
    request: AssetRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    asset = get_asset(db, current_user.id, asset_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="Asset was not found.")
    return save_asset(db, current_user.id, request, asset)


@router.delete("/assets/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_asset(
    asset_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    asset = get_asset(db, current_user.id, asset_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="Asset was not found.")
    delete_asset(db, asset)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/cash-flows",
    response_model=CashFlowResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_cash_flow(
    request: CashFlowRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return save_cash_flow(db, current_user.id, request)


@router.put("/cash-flows/{cash_flow_id}", response_model=CashFlowResponse)
def update_cash_flow(
    cash_flow_id: int,
    request: CashFlowRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    cash_flow = get_cash_flow(db, current_user.id, cash_flow_id)
    if cash_flow is None:
        raise HTTPException(status_code=404, detail="Cash flow was not found.")
    return save_cash_flow(db, current_user.id, request, cash_flow)


@router.delete("/cash-flows/{cash_flow_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_cash_flow(
    cash_flow_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    cash_flow = get_cash_flow(db, current_user.id, cash_flow_id)
    if cash_flow is None:
        raise HTTPException(status_code=404, detail="Cash flow was not found.")
    delete_cash_flow(db, cash_flow)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/debts", response_model=list[DebtResponse])
def get_debts(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return list_debts(db, current_user.id)


@router.post("/debts", response_model=DebtResponse, status_code=status.HTTP_201_CREATED)
def create_debt(request: DebtRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return save_debt(db, current_user.id, request)


@router.put("/debts/{debt_id}", response_model=DebtResponse)
def update_debt(debt_id: int, request: DebtRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    debt = get_debt(db, current_user.id, debt_id)
    if debt is None:
        raise HTTPException(status_code=404, detail="Debt was not found.")
    return save_debt(db, current_user.id, request, debt)


@router.delete("/debts/{debt_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_debt(debt_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    debt = get_debt(db, current_user.id, debt_id)
    if debt is None:
        raise HTTPException(status_code=404, detail="Debt was not found.")
    delete_debt(db, debt)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/recurring-cash-flows", response_model=list[RecurringCashFlowResponse])
def get_recurring_flows(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return list_recurring_cash_flows(db, current_user.id)


@router.post("/recurring-cash-flows", response_model=RecurringCashFlowResponse, status_code=status.HTTP_201_CREATED)
def create_recurring_flow(request: RecurringCashFlowRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return save_recurring_cash_flow(db, current_user.id, request)


@router.put("/recurring-cash-flows/{recurring_id}", response_model=RecurringCashFlowResponse)
def update_recurring_flow(recurring_id: int, request: RecurringCashFlowRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    recurring = get_recurring_cash_flow(db, current_user.id, recurring_id)
    if recurring is None:
        raise HTTPException(status_code=404, detail="Recurring cash flow was not found.")
    return save_recurring_cash_flow(db, current_user.id, request, recurring)


@router.delete("/recurring-cash-flows/{recurring_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_recurring_flow(recurring_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    recurring = get_recurring_cash_flow(db, current_user.id, recurring_id)
    if recurring is None:
        raise HTTPException(status_code=404, detail="Recurring cash flow was not found.")
    delete_recurring_cash_flow(db, recurring)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
