from datetime import date, timedelta
from decimal import Decimal

from app.models.financial import Asset, CashFlow, Debt, RecurringCashFlow
from app.services.financial_service import (
    build_financial_planning_context,
    build_financial_planning_snapshot,
    build_financial_summary,
    month_key,
)


def test_month_key_supports_positive_and_negative_offsets():
    assert month_key(date(2026, 1, 15), -1) == "2025-12"
    assert month_key(date(2026, 12, 15), 1) == "2027-01"


def test_build_financial_summary_combines_assets_debts_cash_flows_and_recurring_items():
    today = date.today()
    assets = [
        Asset(asset_type="cash", name="Savings", amount=Decimal("1000")),
        Asset(asset_type="investment", name="ETF", amount=Decimal("2500")),
    ]
    debts = [
        Debt(debt_type="credit_card", name="Card", balance=Decimal("300")),
    ]
    cash_flows = [
        CashFlow(
            flow_type="income",
            name="Bonus",
            amount=Decimal("500"),
            date=today,
        ),
        CashFlow(
            flow_type="expense",
            name="Groceries",
            amount=Decimal("120"),
            date=today,
        ),
    ]
    recurring_cash_flows = [
        RecurringCashFlow(
            flow_type="income",
            name="Salary",
            amount=Decimal("1200"),
            frequency="weekly",
            start_date=today - timedelta(days=30),
        ),
        RecurringCashFlow(
            flow_type="expense",
            name="Rent",
            amount=Decimal("2000"),
            frequency="monthly",
            start_date=today - timedelta(days=30),
        ),
        RecurringCashFlow(
            flow_type="expense",
            name="Future subscription",
            amount=Decimal("50"),
            frequency="monthly",
            start_date=today + timedelta(days=30),
        ),
    ]

    summary = build_financial_summary(
        assets,
        debts,
        cash_flows,
        recurring_cash_flows,
    )

    assert summary["cash_savings"] == Decimal("1380.00")
    assert summary["total_assets"] == Decimal("3880.00")
    assert summary["total_debts"] == Decimal("300")
    assert summary["net_worth"] == Decimal("3580.00")
    assert summary["monthly_income"] == Decimal("5700.000000000000000000000000")
    assert summary["monthly_expenses"] == Decimal("2120")
    assert summary["monthly_cash_flow"] == Decimal("3580.000000000000000000000000")
    assert summary["asset_allocation"] == [
        {"asset_type": "cash", "amount": Decimal("1380.00")},
        {"asset_type": "investment", "amount": Decimal("2500")},
    ]
    assert summary["debt_breakdown"] == [
        {"debt_type": "credit_card", "amount": Decimal("300")},
    ]
    assert len(summary["cash_savings_trend"]) == 6
    assert summary["cash_savings_trend"][-1]["amount"] == Decimal("1380.00")
    assert summary["recent_cash_flows"] == cash_flows[:5]


def test_build_financial_planning_snapshot_keeps_one_off_and_ongoing_cash_flow_separate():
    as_of = date(2026, 7, 21)
    snapshot = build_financial_planning_snapshot(
        assets=[
            Asset(asset_type="cash", name="Savings", amount=Decimal("4000")),
            Asset(asset_type="property", name="Car", amount=Decimal("8000")),
        ],
        debts=[
            Debt(debt_type="loan", name="Personal loan", balance=Decimal("1500")),
        ],
        cash_flows=[
            CashFlow(
                flow_type="income",
                name="Refund",
                amount=Decimal("300"),
                date=date(2026, 6, 20),
            ),
            CashFlow(
                flow_type="expense",
                name="Bills",
                amount=Decimal("100"),
                date=date(2026, 7, 2),
            ),
            CashFlow(
                flow_type="income",
                name="Gift",
                amount=Decimal("250"),
                date=date(2026, 7, 5),
            ),
        ],
        recurring_cash_flows=[
            RecurringCashFlow(
                flow_type="income",
                name="Salary",
                amount=Decimal("5000"),
                frequency="monthly",
                start_date=date(2026, 1, 1),
            ),
            RecurringCashFlow(
                flow_type="expense",
                name="Rent",
                amount=Decimal("600"),
                frequency="weekly",
                start_date=date(2026, 1, 1),
            ),
            RecurringCashFlow(
                flow_type="income",
                name="Expired allowance",
                amount=Decimal("100"),
                frequency="monthly",
                start_date=date(2026, 1, 1),
                end_date=date(2026, 6, 30),
            ),
        ],
        as_of=as_of,
    )

    assert snapshot.has_financial_records is True
    assert snapshot.has_cash_flow_records is True
    assert snapshot.total_assets == Decimal("12000")
    assert snapshot.total_debts == Decimal("1500")
    assert snapshot.cash_savings == Decimal("4000")
    assert snapshot.ongoing_monthly_income == Decimal("5000")
    assert snapshot.ongoing_monthly_expenses == Decimal("2600.000000000000000000000000")
    assert snapshot.ongoing_monthly_surplus == Decimal("2400.000000000000000000000000")
    assert snapshot.one_off_period == "2026-07"
    assert snapshot.one_off_income == Decimal("250")
    assert snapshot.one_off_expenses == Decimal("100")
    assert snapshot.one_off_surplus == Decimal("150")


def test_build_financial_planning_context_handles_missing_and_available_records():
    empty_snapshot = build_financial_planning_snapshot([], [], [], [], as_of=date(2026, 7, 21))
    empty_context = build_financial_planning_context(empty_snapshot)

    assert "Financial records: none" in empty_context
    assert "do not fabricate income" in empty_context

    populated_snapshot = build_financial_planning_snapshot(
        assets=[Asset(asset_type="cash", name="Savings", amount=Decimal("1000"))],
        debts=[],
        cash_flows=[],
        recurring_cash_flows=[],
        as_of=date(2026, 7, 21),
    )
    populated_context = build_financial_planning_context(populated_snapshot)

    assert "Financial records: available." in populated_context
    assert "Total assets: $1,000.00." in populated_context
    assert "One-off transactions: none recorded." in populated_context
    assert "Income and expense records are missing." in populated_context
