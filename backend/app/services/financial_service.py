from collections import defaultdict
from dataclasses import dataclass
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


def month_key(value: date, offset: int = 0) -> str:
    month_index = value.year * 12 + value.month - 1 + offset
    return f"{month_index // 12:04d}-{month_index % 12 + 1:02d}"


@dataclass(frozen=True)
class FinancialPlanningSnapshot:
    has_financial_records: bool
    has_cash_flow_records: bool
    total_assets: Decimal
    total_debts: Decimal
    cash_savings: Decimal
    ongoing_monthly_income: Decimal
    ongoing_monthly_expenses: Decimal
    one_off_period: str | None
    one_off_income: Decimal
    one_off_expenses: Decimal

    @property
    def ongoing_monthly_surplus(self) -> Decimal:
        return self.ongoing_monthly_income - self.ongoing_monthly_expenses

    @property
    def one_off_surplus(self) -> Decimal:
        return self.one_off_income - self.one_off_expenses


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
    cash_flow_delta = ZERO
    for flow in cash_flows:
        signed_amount = flow.amount if flow.flow_type == "income" else -flow.amount
        cash_flow_delta += signed_amount
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

    # Recurring flows describe earning/spending capacity. They do not move the
    # stored cash balance until an actual cash-flow transaction is recorded.
    cash_asset_balance = allocation["cash"]
    cash_savings = cash_asset_balance + cash_flow_delta
    allocation["cash"] = cash_savings
    non_cash_assets = sum(
        (asset.amount for asset in assets if asset.asset_type != "cash"),
        ZERO,
    )
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
            {
                "month": period,
                "amount": cash_asset_balance + sum(
                    (amount for month, amount in monthly_totals.items() if month <= period),
                    ZERO,
                ),
            }
            for period in (month_key(today, offset) for offset in range(-5, 1))
        ],
        "recent_cash_flows": cash_flows[:5],
    }


def build_financial_planning_snapshot(
    assets: list[Asset],
    debts: list[Debt],
    cash_flows: list[CashFlow],
    recurring_cash_flows: list[RecurringCashFlow],
    as_of: date | None = None,
) -> FinancialPlanningSnapshot:
    """Calculate a goal-planning baseline without mixing cash-flow types."""
    effective_date = as_of or date.today()
    scheduled_monthly_income = ZERO
    scheduled_monthly_expenses = ZERO

    for flow in recurring_cash_flows:
        if flow.start_date > effective_date:
            continue
        if flow.end_date is not None and flow.end_date < effective_date:
            continue
        monthly_amount = flow.amount * MONTHLY_MULTIPLIERS[flow.frequency]
        if flow.flow_type == "income":
            scheduled_monthly_income += monthly_amount
        else:
            scheduled_monthly_expenses += monthly_amount

    one_off_period = max(
        (flow.date.strftime("%Y-%m") for flow in cash_flows),
        default=None,
    )
    one_off_income = ZERO
    one_off_expenses = ZERO
    classified_ongoing_income = ZERO
    classified_ongoing_expenses = ZERO
    if one_off_period is not None:
        for flow in cash_flows:
            if flow.date.strftime("%Y-%m") != one_off_period:
                continue
            ongoing_component = min(
                max(
                    getattr(flow, "ongoing_amount", ZERO) or ZERO,
                    ZERO,
                ),
                flow.amount,
            )
            one_off_component = flow.amount - ongoing_component
            if flow.flow_type == "income":
                classified_ongoing_income += ongoing_component
                one_off_income += one_off_component
            else:
                classified_ongoing_expenses += ongoing_component
                one_off_expenses += one_off_component

    # Scheduled records and a classified statement are alternative evidence
    # for sustainable capacity. Taking the larger per flow type prevents an
    # uploaded salary or bill from being counted twice when the user has also
    # entered its recurring schedule.
    ongoing_monthly_income = max(
        scheduled_monthly_income,
        classified_ongoing_income,
    )
    ongoing_monthly_expenses = max(
        scheduled_monthly_expenses,
        classified_ongoing_expenses,
    )

    return FinancialPlanningSnapshot(
        has_financial_records=bool(
            assets or debts or cash_flows or recurring_cash_flows
        ),
        has_cash_flow_records=bool(cash_flows or recurring_cash_flows),
        total_assets=sum((asset.amount for asset in assets), ZERO),
        total_debts=sum((debt.balance for debt in debts), ZERO),
        cash_savings=sum(
            (
                asset.amount
                for asset in assets
                if asset.asset_type == "cash"
            ),
            ZERO,
        ),
        ongoing_monthly_income=ongoing_monthly_income,
        ongoing_monthly_expenses=ongoing_monthly_expenses,
        one_off_period=one_off_period,
        one_off_income=one_off_income,
        one_off_expenses=one_off_expenses,
    )


def _money(value: Decimal) -> str:
    return f"${value:,.2f}"


def build_financial_planning_context(
    snapshot: FinancialPlanningSnapshot,
) -> str:
    if not snapshot.has_financial_records:
        return (
            "Homepage financial foundation:\n"
            "Financial records: none. The user did not provide an onboarding "
            "financial snapshot and has no later HomePage or PDF records. "
            "For goal planning, still give a complete recommendation using "
            "conservative, clearly labelled assumptions. Use zero as the planning "
            "baseline for unknown current savings, do not fabricate income, "
            "expenses, debts, or available surplus, and do not claim that an "
            "illustrative monthly amount is proven affordable. The user may upload "
            "a bank statement or transaction PDF with the + button later to refine "
            "the plan, but an upload is not a prerequisite for a recommendation."
        )

    lines = [
        "Homepage financial foundation. These are user-owned records and "
        "code-calculated totals. Reuse them instead of asking the user to "
        "repeat known figures:",
        "Financial records: available.",
        f"Total assets: {_money(snapshot.total_assets)}.",
        f"Cash savings: {_money(snapshot.cash_savings)}.",
        f"Total debts: {_money(snapshot.total_debts)}.",
        (
            "Ongoing monthly income: "
            f"{_money(snapshot.ongoing_monthly_income)}."
        ),
        (
            "Ongoing monthly expenses: "
            f"{_money(snapshot.ongoing_monthly_expenses)}."
        ),
        (
            "Ongoing monthly surplus (ongoing income minus ongoing expenses): "
            f"{_money(snapshot.ongoing_monthly_surplus)}."
        ),
    ]

    if snapshot.one_off_period is not None:
        lines.extend(
            [
                f"Latest classified transaction period: {snapshot.one_off_period}.",
                f"One-off income in that period: {_money(snapshot.one_off_income)}.",
                f"One-off expenses in that period: {_money(snapshot.one_off_expenses)}.",
                (
                    "One-off surplus in that period (one-off income minus "
                    f"one-off expenses): {_money(snapshot.one_off_surplus)}."
                ),
            ]
        )
    else:
        lines.append("One-off transactions: none recorded.")

    if not snapshot.has_cash_flow_records:
        lines.append(
            "Income and expense records are missing. Use the available asset "
            "and debt values, but ask for cash-flow information or a PDF before "
            "judging goal affordability."
        )

    lines.append(
        "Keep ongoing and one-off amounts separate. Never use one-off income "
        "to justify an ongoing monthly goal contribution."
    )
    return "\n".join(lines)
