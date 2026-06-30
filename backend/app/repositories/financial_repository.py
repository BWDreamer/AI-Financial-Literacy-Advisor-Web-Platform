from sqlalchemy.orm import Session

from app.models.financial import Asset, CashFlow
from app.schemas.financial import AssetRequest, CashFlowRequest


def list_assets(db: Session, user_id: int) -> list[Asset]:
    return db.query(Asset).filter(Asset.user_id == user_id).order_by(Asset.id).all()


def get_asset(db: Session, user_id: int, asset_id: int) -> Asset | None:
    return db.query(Asset).filter(Asset.id == asset_id, Asset.user_id == user_id).first()


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
