import calendar
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy.orm import Session

from app.models.goal import Goal
from app.repositories.financial_repository import list_assets, list_cash_flows, list_debts, list_recurring_cash_flows
from app.repositories.goal_repository import list_contributions, list_progress
from app.services.financial_service import build_financial_summary


MONEY = Decimal("0.01")
MAX_EXPECTED_CHART_POINTS = 600


def money(value: Decimal) -> Decimal:
    return Decimal(value).quantize(MONEY, rounding=ROUND_HALF_UP)


def months_until(target: date, today: date | None = None) -> int:
    today = today or date.today()
    months = (target.year - today.year) * 12 + target.month - today.month
    if target.day < today.day:
        months -= 1
    return max(months, 0)


def add_months(value: date, count: int) -> date:
    month_index = value.month - 1 + count
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    return date(year, month, min(value.day, calendar.monthrange(year, month)[1]))


def analyse_goal(goal: Goal, today: date | None = None) -> dict:
    today = today or date.today()
    target = Decimal(goal.target_amount)
    current = Decimal(goal.current_amount)
    remaining = max(target - current, Decimal("0"))
    months = months_until(goal.target_date, today)
    required = money(remaining / months) if months else money(remaining)
    contribution = Decimal(goal.monthly_contribution)
    if current >= target:
        state = "completed"
        projected = today
    elif goal.target_date <= today or contribution < required:
        state = "behind"
        projected = add_months(today, int((remaining / contribution).to_integral_value(rounding="ROUND_CEILING"))) if contribution > 0 else None
    else:
        state = "on_track"
        projected = add_months(today, int((remaining / contribution).to_integral_value(rounding="ROUND_CEILING"))) if contribution > 0 else None
    return {
        "progress_percentage": money(min(current / target * 100, Decimal("100"))),
        "required_monthly": required,
        "monthly_difference": money(contribution - required),
        "months_remaining": months,
        "projected_completion_date": projected,
        "status": state,
    }


def refresh_goal_status(goal: Goal) -> None:
    goal.status = analyse_goal(goal)["status"]


def build_goal_chart(db: Session, goal: Goal) -> dict:
    progress = list_progress(db, goal.id)
    contributions = list_contributions(db, goal.id)
    events = [(item.progress_date, Decimal(item.amount)) for item in progress]
    events += [(item.created_at.date(), Decimal(item.amount)) for item in contributions]
    events.sort(key=lambda item: item[0])
    baseline = max(Decimal(goal.current_amount) - sum((item[1] for item in events), Decimal("0")), Decimal("0"))
    actual = [{"date": goal.created_at.date(), "amount": money(baseline)}]
    running = baseline
    for event_date, amount in events:
        running += amount
        actual.append({"date": event_date, "amount": money(running)})

    start = goal.created_at.date()
    total_months = max((goal.target_date.year - start.year) * 12 + goal.target_date.month - start.month, 1)
    needs_final_target = add_months(start, total_months) != goal.target_date
    monthly_point_limit = MAX_EXPECTED_CHART_POINTS - int(needs_final_target)
    if total_months + 1 <= monthly_point_limit:
        expected_indices = range(total_months + 1)
    else:
        expected_indices = (
            sample_index * total_months // (monthly_point_limit - 1)
            for sample_index in range(monthly_point_limit)
        )
    expected = []
    for index in expected_indices:
        point_date = min(add_months(start, index), goal.target_date)
        expected.append({"date": point_date, "amount": money(Decimal(goal.target_amount) * index / total_months)})
        if point_date == goal.target_date:
            break
    if expected[-1]["date"] != goal.target_date:
        expected.append({"date": goal.target_date, "amount": money(Decimal(goal.target_amount))})
    return {"actual_progress_points": actual, "expected_progress_points": expected, "target_amount": goal.target_amount}


def financial_numbers(db: Session, user_id: int) -> dict:
    return build_financial_summary(
        list_assets(db, user_id), list_debts(db, user_id),
        list_cash_flows(db, user_id), list_recurring_cash_flows(db, user_id),
    )


def validate_owned_ratios(goals: list[Goal], ratios: list) -> None:
    owned = {goal.id for goal in goals}
    missing = [item.goal_id for item in ratios if item.goal_id not in owned]
    if missing:
        raise ValueError(f"Goals not found: {missing}")


def calculate_monthly_allocation(finance: dict, ratio: Decimal, goal_ratios: list) -> dict:
    net = money(max(Decimal(finance["monthly_income"]) - Decimal(finance["monthly_expenses"]), Decimal("0")))
    allocatable = money(net * ratio / 100)
    rows = [
        {"goal_id": int(item.goal_id), "ratio": Decimal(str(item.ratio)), "monthly_amount": money(allocatable * Decimal(str(item.ratio)) / 100)}
        for item in goal_ratios
    ]
    assigned = money(sum((item["monthly_amount"] for item in rows), Decimal("0")))
    return {
        "monthly_net_income": net,
        "monthly_allocatable": allocatable,
        "already_assigned": assigned,
        "unassigned": money(max(allocatable - assigned, Decimal("0"))),
        "goals": rows,
    }
