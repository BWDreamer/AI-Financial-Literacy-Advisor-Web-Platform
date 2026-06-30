from collections import defaultdict
from datetime import date
from decimal import Decimal

from app.models.financial import Asset, CashFlow


ZERO = Decimal("0.00")


def build_financial_summary(assets: list[Asset], cash_flows: list[CashFlow]) -> dict:
    today = date.today()
    allocation: dict[str, Decimal] = defaultdict(lambda: ZERO)
    monthly_totals: dict[str, Decimal] = defaultdict(lambda: ZERO)

    for asset in assets:
        allocation[asset.asset_type] += asset.amount

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

    return {
        "net_worth": sum((asset.amount for asset in assets), ZERO),
        "cash_savings": allocation["cash"],
        "monthly_income": monthly_income,
        "monthly_expenses": monthly_expenses,
        "monthly_cash_flow": monthly_income - monthly_expenses,
        "asset_allocation": [
            {"asset_type": asset_type, "amount": amount}
            for asset_type, amount in sorted(allocation.items())
        ],
        "cash_savings_trend": [
            {"month": month, "amount": amount}
            for month, amount in sorted(monthly_totals.items())[-6:]
        ],
        "recent_cash_flows": cash_flows[:5],
    }
