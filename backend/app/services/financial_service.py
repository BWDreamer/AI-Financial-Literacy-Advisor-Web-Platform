from collections import defaultdict
from datetime import date
from decimal import Decimal

from app.models.financial import Asset, CashFlow, Debt, RecurringCashFlow


ZERO = Decimal("0.00")


def monthly_amount(flow: RecurringCashFlow) -> Decimal:
    if flow.frequency == "weekly":
        return flow.amount * Decimal("52") / Decimal("12")
    if flow.frequency == "fortnightly":
        return flow.amount * Decimal("26") / Decimal("12")
    if flow.frequency == "yearly":
        return flow.amount / Decimal("12")
    return flow.amount


def is_active_recurring(flow: RecurringCashFlow, today: date) -> bool:
    if flow.start_date > today:
        return False
    return flow.end_date is None or flow.end_date >= today


def build_financial_summary(
    assets: list[Asset],
    cash_flows: list[CashFlow],
    debts: list[Debt] | None = None,
    recurring_cash_flows: list[RecurringCashFlow] | None = None,
) -> dict:
    today = date.today()
    allocation: dict[str, Decimal] = defaultdict(lambda: ZERO)
    debt_breakdown: dict[str, Decimal] = defaultdict(lambda: ZERO)
    monthly_totals: dict[str, Decimal] = defaultdict(lambda: ZERO)
    debts = debts or []
    recurring_cash_flows = recurring_cash_flows or []

    for asset in assets:
        allocation[asset.asset_type] += asset.amount

    for debt in debts:
        debt_breakdown[debt.debt_type] += debt.balance

    monthly_income = ZERO
    monthly_expenses = ZERO
    recurring_income = ZERO
    recurring_expenses = ZERO
    for flow in cash_flows:
        signed_amount = flow.amount if flow.flow_type == "income" else -flow.amount
        monthly_totals[flow.date.strftime("%Y-%m")] += signed_amount
        if flow.date.year == today.year and flow.date.month == today.month:
            if flow.flow_type == "income":
                monthly_income += flow.amount
            else:
                monthly_expenses += flow.amount

    for flow in recurring_cash_flows:
        if not is_active_recurring(flow, today):
            continue
        amount = monthly_amount(flow)
        if flow.flow_type == "income":
            monthly_income += amount
            recurring_income += amount
        else:
            monthly_expenses += amount
            recurring_expenses += amount

    non_cash_assets = sum((asset.amount for asset in assets if asset.asset_type != "cash"), ZERO)
    cash_flow_delta = sum(
        (flow.amount if flow.flow_type == "income" else -flow.amount for flow in cash_flows),
        ZERO,
    )
    recurring_delta = recurring_income - recurring_expenses
    cash_savings = allocation["cash"] + cash_flow_delta + recurring_delta
    allocation["cash"] = cash_savings
    total_assets = non_cash_assets + cash_savings
    total_debts = sum((debt.balance for debt in debts), ZERO)
    return {
        "total_assets": total_assets,
        "total_debts": total_debts,
        "net_worth": total_assets - total_debts,
        "cash_savings": cash_savings,
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
