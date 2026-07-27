from datetime import date
from decimal import Decimal

from app.repositories.financial_repository import (
    delete_asset,
    delete_cash_bucket,
    delete_cash_flow,
    delete_debt,
    delete_recurring_cash_flow,
    get_asset,
    get_asset_by_type_and_name,
    get_cash_bucket,
    get_cash_flow,
    get_cash_flow_by_identity,
    get_debt,
    get_recurring_cash_flow,
    list_assets,
    list_cash_buckets,
    list_cash_flows,
    list_debts,
    list_recurring_cash_flows,
    save_asset,
    save_cash_bucket,
    save_cash_flow,
    save_debt,
    save_recurring_cash_flow,
)
from app.repositories.user_repository import create_user
from app.schemas.financial import (
    AssetRequest,
    CashBucketRequest,
    CashFlowRequest,
    DebtRequest,
    RecurringCashFlowRequest,
)


def test_asset_repository_crud_and_identity_lookup(db_session):
    user = create_user(db_session, email="asset@example.com", password_hash="hash")
    asset = save_asset(
        db_session,
        user.id,
        AssetRequest(asset_type="cash", name="Emergency fund", amount=Decimal("5000")),
    )

    assert get_asset(db_session, user.id, asset.id).id == asset.id
    assert get_asset_by_type_and_name(db_session, user.id, "cash", "Emergency fund").id == asset.id
    assert list_assets(db_session, user.id) == [asset]

    updated = save_asset(
        db_session,
        user.id,
        AssetRequest(asset_type="cash", name="Emergency fund", amount=Decimal("6000")),
        asset=asset,
    )
    assert updated.amount == Decimal("6000.00")

    delete_asset(db_session, asset)
    assert list_assets(db_session, user.id) == []


def test_cash_flow_repository_crud_ordering_and_identity_lookup(db_session):
    user = create_user(db_session, email="flow@example.com", password_hash="hash")
    older = save_cash_flow(
        db_session,
        user.id,
        CashFlowRequest(
            flow_type="expense",
            name="Rent",
            amount=Decimal("2300"),
            date=date(2026, 7, 1),
        ),
    )
    newer = save_cash_flow(
        db_session,
        user.id,
        CashFlowRequest(
            flow_type="income",
            name="Salary",
            amount=Decimal("7000"),
            date=date(2026, 7, 15),
        ),
    )

    assert get_cash_flow(db_session, user.id, older.id).id == older.id
    assert get_cash_flow_by_identity(
        db_session,
        user.id,
        "income",
        "Salary",
        date(2026, 7, 15),
    ).id == newer.id
    assert list_cash_flows(db_session, user.id) == [newer, older]

    delete_cash_flow(db_session, older)
    assert list_cash_flows(db_session, user.id) == [newer]


def test_debt_recurring_cash_flow_and_bucket_crud(db_session):
    user = create_user(db_session, email="financial@example.com", password_hash="hash")

    debt = save_debt(
        db_session,
        user.id,
        DebtRequest(
            debt_type="credit_card",
            name="Card",
            balance=Decimal("1200"),
            minimum_payment=Decimal("100"),
            interest_rate=Decimal("19.99"),
        ),
    )
    recurring = save_recurring_cash_flow(
        db_session,
        user.id,
        RecurringCashFlowRequest(
            flow_type="expense",
            name="Internet",
            amount=Decimal("80"),
            frequency="monthly",
            start_date=date(2026, 7, 1),
            category="Bills",
        ),
    )
    bucket = save_cash_bucket(
        db_session,
        user.id,
        CashBucketRequest(
            bucket_type="emergency_fund",
            name="Emergency",
            amount=Decimal("3000"),
        ),
    )

    assert get_debt(db_session, user.id, debt.id).name == "Card"
    assert list_debts(db_session, user.id) == [debt]
    assert get_recurring_cash_flow(db_session, user.id, recurring.id).name == "Internet"
    assert list_recurring_cash_flows(db_session, user.id) == [recurring]
    assert get_cash_bucket(db_session, user.id, bucket.id).name == "Emergency"
    assert list_cash_buckets(db_session, user.id) == [bucket]

    delete_debt(db_session, debt)
    delete_recurring_cash_flow(db_session, recurring)
    delete_cash_bucket(db_session, bucket)

    assert list_debts(db_session, user.id) == []
    assert list_recurring_cash_flows(db_session, user.id) == []
    assert list_cash_buckets(db_session, user.id) == []
