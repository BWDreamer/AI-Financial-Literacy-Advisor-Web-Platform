import calendar
import hashlib
import json
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from types import SimpleNamespace
from typing import Any

from sqlalchemy.orm import Session

from app.models.financial import CashBucket
from app.models.goal import Goal, GoalProgress
from app.repositories.financial_repository import list_assets, list_cash_buckets, list_cash_flows, list_debts, list_recurring_cash_flows
from app.repositories.goal_repository import list_progress
from app.services.financial_service import (
    FinancialPlanningSnapshot,
    build_financial_planning_snapshot,
    build_financial_summary,
)
from app.services.goal_allocation_service import (
    calculate_goal_allocations,
    months_until,
)
from app.schemas.goal import GoalPreviewRequest, GoalRequest
from app.services.goal_ratio_service import (
    MAX_GOAL_RATIO,
    normalize_goal_ratio_rows,
    ratio_percent,
)
from app.services.goal_planning_service import (
    GoalCategory,
    GoalPlanningState,
    GoalRecommendationStatus,
    emergency_fund_target_amount,
)


MONEY = Decimal("0.01")
MAX_EXPECTED_CHART_POINTS = 600
GOAL_STORAGE_CATEGORIES = {
    GoalCategory.GENERAL_SAVING: "General Saving",
    GoalCategory.EMERGENCY_FUND: "Emergency Fund",
    GoalCategory.DEBT_REPAYMENT: "Debt Repayment",
    GoalCategory.HOME_DEPOSIT: "Home Deposit",
    GoalCategory.RETIREMENT: "Retirement",
    GoalCategory.BUDGET: "Budget",
}


@dataclass(frozen=True)
class ConfirmedGoalPlan:
    fingerprint: str
    goals: tuple[Goal, ...]
    one_off_allocations: tuple[Decimal, ...]
    monthly_ratios: tuple[Decimal, ...]


def money(value: Decimal) -> Decimal:
    return Decimal(value).quantize(MONEY, rounding=ROUND_HALF_UP)


def add_months(value: date, count: int) -> date:
    month_index = value.month - 1 + count
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    return date(year, month, min(value.day, calendar.monthrange(year, month)[1]))


def previous_month_end(today: date | None = None) -> date:
    today = today or date.today()
    first_day = today.replace(day=1)
    return first_day - timedelta(days=1)


def analyse_goal(goal: Goal, today: date | None = None, allocated_monthly: Decimal | None = None, cash_allocation: Decimal | None = None) -> dict:
    today = today or date.today()
    target = Decimal(goal.target_amount)
    current = Decimal(goal.current_amount)
    remaining = max(target - current, Decimal("0"))
    months = months_until(goal.target_date, today)
    required = money(remaining / months) if months else money(remaining)
    contribution = Decimal(allocated_monthly if allocated_monthly is not None else goal.monthly_contribution)
    if current >= target:
        state = "completed" if getattr(goal, "status", "") == "completed" else "pending_archive"
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
        "allocated_monthly": money(contribution),
        "cash_allocation": money(cash_allocation or Decimal("0")),
        "months_remaining": months,
        "projected_completion_date": projected,
        "status": state,
    }


def refresh_goal_status(goal: Goal) -> None:
    goal.status = analyse_goal(goal)["status"]


def linked_cash_allocation(db: Session, goal: Goal) -> Decimal:
    bucket = db.query(CashBucket).filter(
        CashBucket.user_id == goal.user_id,
        CashBucket.goal_id == goal.id,
        CashBucket.bucket_type == "goal_reserved",
    ).first()
    if bucket is not None:
        return money(Decimal(bucket.amount))
    if goal.status == "completed" or goal.archived:
        return Decimal("0.00")
    return money(Decimal(goal.current_amount))


def sync_goal_reserved_cash(db: Session, goal: Goal) -> bool:
    bucket = db.query(CashBucket).filter(
        CashBucket.user_id == goal.user_id,
        CashBucket.goal_id == goal.id,
        CashBucket.bucket_type == "goal_reserved",
    ).first()
    amount = money(Decimal(goal.current_amount))
    if amount <= 0 or goal.archived or goal.status == "completed":
        if bucket is not None:
            db.delete(bucket)
            return True
        return False
    bucket = bucket or CashBucket(user_id=goal.user_id, goal_id=goal.id, bucket_type="goal_reserved")
    changed = bucket.amount != amount or bucket.name != goal.name
    bucket.name = goal.name
    bucket.amount = amount
    db.add(bucket)
    return changed


def build_goal_preview(request: GoalPreviewRequest) -> dict:
    details = request.category_details

    def amount(field: str) -> Decimal:
        try:
            return Decimal(str(details.get(field) or 0))
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{field} must be a valid number.") from exc

    common = {
        "category": request.category, "target_date": request.target_date,
        "priority": {"High": 1, "Medium": 3, "Low": 5}[request.priority],
        "category_details": details,
    }
    if request.category == "Emergency Fund":
        values = {
            "name": "Emergency Fund",
            "target_amount": emergency_fund_target_amount(details),
            "current_amount": amount("current_amount"),
            "monthly_contribution": amount("monthly_contribution"),
        }
    elif request.category == "Debt Repayment":
        values = {
            "name": str(details.get("debt_name") or "Debt Repayment"),
            "target_amount": amount("debt_balance"), "current_amount": Decimal("0"),
            "monthly_contribution": amount("minimum_repayment") + amount("extra_repayment"),
        }
    elif request.category == "Home Deposit":
        calculated = amount("property_price") * amount("deposit_percent") / 100
        values = {
            "name": "Home Deposit",
            "target_amount": max(amount("deposit_target"), calculated) + amount("cost_buffer"),
            "current_amount": amount("current_amount"),
            "monthly_contribution": amount("monthly_contribution"),
        }
    elif request.category == "Retirement":
        values = {
            "name": "Retirement Plan", "target_amount": amount("target_amount"),
            "current_amount": amount("current_super"),
            "monthly_contribution": amount("regular_contribution"),
        }
    elif request.category == "Budget":
        values = {
            "name": "Improve Monthly Cash Flow",
            "target_amount": amount("target_monthly_surplus") * 12,
            "current_amount": Decimal("0"),
            "monthly_contribution": amount("target_monthly_surplus"),
        }
    elif request.category == "General Saving":
        values = {
            "name": str(details.get("goal_title") or "General Saving"),
            "target_amount": amount("target_amount"),
            "current_amount": amount("current_amount"),
            "monthly_contribution": amount("monthly_contribution"),
        }
    else:
        raise ValueError("Unsupported goal category.")

    goal = GoalRequest(**common, **values)
    analysis = analyse_goal(SimpleNamespace(**goal.model_dump()))
    return {"goal": goal, "analysis": analysis}


def _json_safe_category_details(
    answers: dict[str, Any],
) -> dict[str, Any]:
    details: dict[str, Any] = {}
    for field, value in answers.items():
        if isinstance(value, date):
            details[field] = value.isoformat()
        elif isinstance(value, Decimal):
            details[field] = format(value, "f")
        else:
            details[field] = value
    return details


def build_confirmed_goal_plan(
    state: GoalPlanningState,
    user_id: int,
    snapshot: FinancialPlanningSnapshot,
) -> ConfirmedGoalPlan:
    """Convert an accepted AI plan into validated MyGoals records."""
    if state.recommendation_status != GoalRecommendationStatus.ACCEPTED:
        raise ValueError("Only an accepted goal plan can be saved.")
    if not state.goals:
        raise ValueError("An accepted goal plan must contain at least one goal.")

    allocations, _, _ = calculate_goal_allocations(state, snapshot)
    allocation_iterator = iter(allocations)
    recurring_basis = max(snapshot.ongoing_monthly_surplus, Decimal("0"))
    requests: list[GoalRequest] = []
    goals: list[Goal] = []
    one_off_allocations: list[Decimal] = []
    monthly_ratios: list[Decimal] = []
    for planned_goal in state.goals:
        if planned_goal.priority is None:
            raise ValueError("Every confirmed goal must have a priority.")
        details = _json_safe_category_details(planned_goal.answers)
        preview = build_goal_preview(
            GoalPreviewRequest(
                category=GOAL_STORAGE_CATEGORIES[planned_goal.category],
                target_date=planned_goal.answers["deadline"],
                priority=planned_goal.priority.value,
                category_details=details,
            )
        )
        request = preview["goal"]
        one_off_amount = Decimal("0")
        monthly_ratio = Decimal("0")
        if planned_goal.category != GoalCategory.BUDGET:
            allocation = next(allocation_iterator)
            one_off_amount = allocation.one_off_amount
            current_amount = money(
                min(
                    request.target_amount,
                    request.current_amount + one_off_amount,
                )
            )
            details = dict(request.category_details)
            details["confirmed_one_off_allocation"] = format(
                one_off_amount,
                "f",
            )
            details["confirmed_monthly_allocation"] = format(
                allocation.recurring_monthly_amount,
                "f",
            )
            if "current_amount" in details:
                details["current_amount"] = format(current_amount, "f")
            if "current_super" in details:
                details["current_super"] = format(current_amount, "f")
            if "monthly_contribution" in details:
                details["monthly_contribution"] = format(
                    allocation.recurring_monthly_amount,
                    "f",
                )
            if "regular_contribution" in details:
                details["regular_contribution"] = format(
                    allocation.recurring_monthly_amount,
                    "f",
                )
            request = GoalRequest(
                **{
                    **request.model_dump(),
                    "current_amount": current_amount,
                    "monthly_contribution": (
                        allocation.recurring_monthly_amount
                    ),
                    "category_details": details,
                }
            )
            if recurring_basis > 0:
                monthly_ratio = ratio_percent(
                    allocation.recurring_monthly_amount
                    / recurring_basis
                    * Decimal("100")
                )
        goal = Goal(user_id=user_id, **request.model_dump())
        refresh_goal_status(goal)
        requests.append(request)
        goals.append(goal)
        one_off_allocations.append(one_off_amount)
        monthly_ratios.append(monthly_ratio)

    fingerprint_payload = [
        request.model_dump(mode="json")
        for request in requests
    ]
    fingerprint = hashlib.sha256(
        json.dumps(
            fingerprint_payload,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    return ConfirmedGoalPlan(
        fingerprint=fingerprint,
        goals=tuple(goals),
        one_off_allocations=tuple(one_off_allocations),
        monthly_ratios=tuple(monthly_ratios),
    )


def build_goal_chart(db: Session, goal: Goal) -> dict:
    progress = list_progress(db, goal.id)
    events = [(item.progress_date, Decimal(item.amount)) for item in progress]
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
    assets = list_assets(db, user_id)
    debts = list_debts(db, user_id)
    cash_flows = list_cash_flows(db, user_id)
    recurring_cash_flows = list_recurring_cash_flows(db, user_id)
    summary = build_financial_summary(
        assets,
        debts,
        cash_flows,
        recurring_cash_flows,
    )
    snapshot = build_financial_planning_snapshot(
        assets,
        debts,
        cash_flows,
        recurring_cash_flows,
    )
    summary["monthly_income"] = snapshot.ongoing_monthly_income
    summary["monthly_expenses"] = snapshot.ongoing_monthly_expenses
    summary["monthly_cash_flow"] = snapshot.ongoing_monthly_surplus
    summary["cash_buckets"] = list_cash_buckets(db, user_id)
    return summary


def monthly_allocation_map(db: Session, user_id: int, settings) -> dict[int, Decimal]:
    monthly = calculate_monthly_allocation(
        financial_numbers(db, user_id),
        Decimal(settings.monthly_allocatable_ratio),
        active_goal_ratios(db.query(Goal).filter(
            Goal.user_id == user_id,
            Goal.archived.is_(False),
        ).all(), settings.goal_monthly_ratios or []),
    )
    return {int(row["goal_id"]): Decimal(row["monthly_amount"]) for row in monthly["goals"]}


def active_goal_ratios(goals: list[Goal], ratios: list) -> list:
    active_ids = {goal.id for goal in goals if goal.status != "completed" and not goal.archived}
    return [item for item in ratios if int(item["goal_id"] if isinstance(item, dict) else item.goal_id) in active_ids]


def backfill_goal_ratios(goals: list[Goal], finance: dict, settings) -> bool:
    stored_rows = settings.goal_monthly_ratios or []
    active_stored_rows = active_goal_ratios(goals, stored_rows)
    if active_stored_rows:
        normalized_rows = normalize_goal_ratio_rows(active_stored_rows)
        if normalized_rows == stored_rows:
            return False
        settings.goal_monthly_ratios = normalized_rows
        return True

    net = max(Decimal(finance["monthly_income"]) - Decimal(finance["monthly_expenses"]), Decimal("0"))
    allocatable = money(net * Decimal(settings.monthly_allocatable_ratio) / 100)
    if allocatable <= 0:
        if stored_rows:
            settings.goal_monthly_ratios = []
            return True
        return False
    rows = []
    for goal in goals:
        if goal.status == "completed" or goal.archived:
            continue
        ratio = ratio_percent(
            Decimal(goal.monthly_contribution) / allocatable * 100
        )
        if ratio > 0:
            rows.append(
                {
                    "goal_id": goal.id,
                    "ratio": str(
                        ratio_percent(min(ratio, MAX_GOAL_RATIO))
                    ),
                }
            )
    if not rows:
        if stored_rows:
            settings.goal_monthly_ratios = []
            return True
        return False
    settings.goal_monthly_ratios = normalize_goal_ratio_rows(rows)
    return True


def sync_goal_monthly_ratio(db: Session, goal: Goal) -> None:
    finance = financial_numbers(db, goal.user_id)
    settings = db.merge(goal_settings_proxy(db, goal.user_id))
    net = max(Decimal(finance["monthly_income"]) - Decimal(finance["monthly_expenses"]), Decimal("0"))
    allocatable = money(net * Decimal(settings.monthly_allocatable_ratio) / 100)
    rows = []
    for item in settings.goal_monthly_ratios or []:
        if int(item["goal_id"]) != goal.id:
            rows.append(
                {
                    "goal_id": int(item["goal_id"]),
                    "ratio": str(
                        ratio_percent(Decimal(str(item["ratio"])))
                    ),
                }
            )
    if goal.status == "completed" or goal.archived:
        settings.goal_monthly_ratios = normalize_goal_ratio_rows(rows)
        db.add(settings)
        return
    if allocatable > 0 and Decimal(goal.monthly_contribution) > 0:
        rows.append(
            {
                "goal_id": goal.id,
                "ratio": str(
                    ratio_percent(
                        Decimal(goal.monthly_contribution)
                        / allocatable
                        * 100
                    )
                ),
            }
        )
    settings.goal_monthly_ratios = normalize_goal_ratio_rows(rows)
    db.add(settings)


def goal_settings_proxy(db: Session, user_id: int):
    from app.repositories.goal_repository import get_allocation_settings
    return get_allocation_settings(db, user_id)


def apply_due_monthly_progress(db: Session, goals: list[Goal], monthly_map: dict[int, Decimal], today: date | None = None) -> bool:
    cutoff = previous_month_end(today)
    changed = False
    for goal in goals:
        if goal.status == "completed" or goal.archived:
            continue
        amount = money(monthly_map.get(goal.id, Decimal("0")))
        if amount <= 0:
            continue
        progress_date = goal.created_at.date().replace(day=1)
        while progress_date <= cutoff and progress_date <= goal.target_date:
            final_day = calendar.monthrange(progress_date.year, progress_date.month)[1]
            due_date = progress_date.replace(day=final_day)
            exists = db.query(GoalProgress).filter(
                GoalProgress.goal_id == goal.id,
                GoalProgress.source == "monthly_allocation",
                GoalProgress.progress_date == due_date,
            ).first()
            if not exists:
                remaining = Decimal(goal.target_amount) - Decimal(goal.current_amount)
                contribution = money(min(amount, max(remaining, Decimal("0"))))
                if contribution > 0:
                    goal.current_amount = money(Decimal(goal.current_amount) + contribution)
                    db.add(GoalProgress(
                        goal_id=goal.id, amount=contribution, progress_date=due_date,
                        note="Monthly goal allocation", source="monthly_allocation",
                        new_current_amount=goal.current_amount,
                    ))
                    changed = True
            progress_date = add_months(progress_date, 1)
    return changed


def validate_owned_ratios(goals: list[Goal], ratios: list) -> None:
    owned = {goal.id for goal in goals}
    missing = [item.goal_id for item in ratios if item.goal_id not in owned]
    if missing:
        raise ValueError(f"Goals not found: {missing}")


def calculate_monthly_allocation(finance: dict, ratio: Decimal, goal_ratios: list) -> dict:
    net = money(max(Decimal(finance["monthly_income"]) - Decimal(finance["monthly_expenses"]), Decimal("0")))
    allocatable = money(net * ratio / 100)
    rows = []
    for item in normalize_goal_ratio_rows(goal_ratios):
        goal_id = item["goal_id"] if isinstance(item, dict) else item.goal_id
        goal_ratio = item["ratio"] if isinstance(item, dict) else item.ratio
        goal_ratio = Decimal(str(goal_ratio))
        rows.append({
            "goal_id": int(goal_id), "ratio": goal_ratio,
            "monthly_amount": money(allocatable * goal_ratio / 100),
        })
    assigned = money(sum((item["monthly_amount"] for item in rows), Decimal("0")))
    return {
        "monthly_net_income": net,
        "monthly_allocatable": allocatable,
        "already_assigned": assigned,
        "unassigned": money(max(allocatable - assigned, Decimal("0"))),
        "goals": rows,
    }
