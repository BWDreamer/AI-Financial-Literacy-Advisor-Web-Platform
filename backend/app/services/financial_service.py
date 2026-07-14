from collections import defaultdict
from datetime import date
from decimal import Decimal

from app.models.financial import Asset, CashFlow, Debt, RecurringCashFlow


ZERO = Decimal("0.00")


MONTHLY_MULTIPLIERS = {
    "weekly": Decimal("52") / Decimal("12"),
    "fortnightly": Decimal("26") / Decimal("12"),
    "monthly": Decimal("1"),
    "yearly": Decimal("1") / Decimal("12"),
}


def build_financial_summary(
    assets: list[Asset],
    debts: list[Debt],
    cash_flows: list[CashFlow],
    recurring_cash_flows: list[RecurringCashFlow],
) -> dict:
    today = date.today()
    allocation: dict[str, Decimal] = defaultdict(lambda: ZERO)
    monthly_totals: dict[str, Decimal] = defaultdict(lambda: ZERO)

    for asset in assets:
        allocation[asset.asset_type] += asset.amount

    debt_breakdown: dict[str, Decimal] = defaultdict(lambda: ZERO)
    for debt in debts:
        debt_breakdown[debt.debt_type] += debt.balance

    monthly_income = ZERO
    monthly_expenses = ZERO
    for flow in cash_flows:
        signed_amount = flow.amount if flow.flow_type == "income" else -flow.amount
        monthly_totals[flow.date.strftime("%Y-%m")] += signed_amount
        if flow.date.year == today.year and flow.date.month == today.month:
            if flow.flow_type == "income":
                monthly_income += flow.amount
            else:
                monthly_expenses += flow.amount

    for flow in recurring_cash_flows:
        if flow.start_date > today or (flow.end_date is not None and flow.end_date < today):
            continue
        monthly_amount = flow.amount * MONTHLY_MULTIPLIERS[flow.frequency]
        if flow.flow_type == "income":
            monthly_income += monthly_amount
        else:
            monthly_expenses += monthly_amount

    total_assets = sum((asset.amount for asset in assets), ZERO)
    total_debts = sum((debt.balance for debt in debts), ZERO)

    return {
        "total_assets": total_assets,
        "total_debts": total_debts,
        "net_worth": total_assets - total_debts,
        "cash_savings": allocation["cash"],
        "monthly_income": monthly_income,
        "monthly_expenses": monthly_expenses,
        "monthly_cash_flow": monthly_income - monthly_expenses,
        "asset_allocation": [
            {"asset_type": asset_type, "amount": amount}
            for asset_type, amount in sorted(allocation.items())
        ],
        "debt_breakdown": [
            {"debt_type": debt_type, "amount": amount}
            for debt_type, amount in sorted(debt_breakdown.items())
        ],
        "cash_savings_trend": [
            {"month": month, "amount": amount}
            for month, amount in sorted(monthly_totals.items())[-6:]
        ],
        "recent_cash_flows": cash_flows[:5],
    }
