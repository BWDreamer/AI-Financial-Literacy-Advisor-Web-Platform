from datetime import date as Date

from sqlalchemy.orm import Session

from app.models.financial import Asset, CashFlow, Debt, RecurringCashFlow
from app.schemas.financial import AssetRequest, CashFlowRequest, DebtRequest, RecurringCashFlowRequest


def list_assets(db: Session, user_id: int) -> list[Asset]:
    return db.query(Asset).filter(Asset.user_id == user_id).order_by(Asset.id).all()


def get_asset(db: Session, user_id: int, asset_id: int) -> Asset | None:
    return db.query(Asset).filter(Asset.id == asset_id, Asset.user_id == user_id).first()


def get_asset_by_type_and_name(
    db: Session,
    user_id: int,
    asset_type: str,
    name: str,
) -> Asset | None:
    return (
        db.query(Asset)
        .filter(
            Asset.user_id == user_id,
            Asset.asset_type == asset_type,
            Asset.name == name,
        )
        .first()
    )


def save_asset(db: Session, user_id: int, data: AssetRequest, asset: Asset | None = None) -> Asset:
    asset = asset or Asset(user_id=user_id)
    asset.asset_type = data.asset_type
    asset.name = data.name
    asset.amount = data.amount
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return asset


def delete_asset(db: Session, asset: Asset) -> None:
    db.delete(asset)
    db.commit()


def list_cash_flows(db: Session, user_id: int) -> list[CashFlow]:
    return (
        db.query(CashFlow)
        .filter(CashFlow.user_id == user_id)
        .order_by(CashFlow.date.desc(), CashFlow.id.desc())
        .all()
    )


def get_cash_flow(db: Session, user_id: int, cash_flow_id: int) -> CashFlow | None:
    return db.query(CashFlow).filter(
        CashFlow.id == cash_flow_id,
        CashFlow.user_id == user_id,
    ).first()


def get_cash_flow_by_identity(
    db: Session,
    user_id: int,
    flow_type: str,
    name: str,
    date: Date,
) -> CashFlow | None:
    return (
        db.query(CashFlow)
        .filter(
            CashFlow.user_id == user_id,
            CashFlow.flow_type == flow_type,
            CashFlow.name == name,
            CashFlow.date == date,
        )
        .first()
    )


def save_cash_flow(
    db: Session,
    user_id: int,
    data: CashFlowRequest,
    cash_flow: CashFlow | None = None,
) -> CashFlow:
    cash_flow = cash_flow or CashFlow(user_id=user_id)
    cash_flow.flow_type = data.flow_type
    cash_flow.name = data.name
    cash_flow.amount = data.amount
    cash_flow.date = data.date
    db.add(cash_flow)
    db.commit()
    db.refresh(cash_flow)
    return cash_flow


def delete_cash_flow(db: Session, cash_flow: CashFlow) -> None:
    db.delete(cash_flow)
    db.commit()


def list_debts(db: Session, user_id: int) -> list[Debt]:
    return db.query(Debt).filter(Debt.user_id == user_id).order_by(Debt.id).all()


def get_debt(db: Session, user_id: int, debt_id: int) -> Debt | None:
    return db.query(Debt).filter(Debt.id == debt_id, Debt.user_id == user_id).first()


def save_debt(db: Session, user_id: int, data: DebtRequest, debt: Debt | None = None) -> Debt:
    debt = debt or Debt(user_id=user_id)
    for field, value in data.model_dump().items():
        setattr(debt, field, value)
    db.add(debt)
    db.commit()
    db.refresh(debt)
    return debt


def delete_debt(db: Session, debt: Debt) -> None:
    db.delete(debt)
    db.commit()


def list_recurring_cash_flows(db: Session, user_id: int) -> list[RecurringCashFlow]:
    return (
        db.query(RecurringCashFlow)
        .filter(RecurringCashFlow.user_id == user_id)
        .order_by(RecurringCashFlow.start_date.desc(), RecurringCashFlow.id.desc())
        .all()
    )


def get_recurring_cash_flow(db: Session, user_id: int, recurring_id: int) -> RecurringCashFlow | None:
    return db.query(RecurringCashFlow).filter(
        RecurringCashFlow.id == recurring_id,
        RecurringCashFlow.user_id == user_id,
    ).first()


def save_recurring_cash_flow(
    db: Session,
    user_id: int,
    data: RecurringCashFlowRequest,
    recurring: RecurringCashFlow | None = None,
) -> RecurringCashFlow:
    recurring = recurring or RecurringCashFlow(user_id=user_id)
    for field, value in data.model_dump().items():
        setattr(recurring, field, value)
    db.add(recurring)
    db.commit()
    db.refresh(recurring)
    return recurring


def delete_recurring_cash_flow(db: Session, recurring: RecurringCashFlow) -> None:
    db.delete(recurring)
    db.commit()
