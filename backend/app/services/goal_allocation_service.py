from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_DOWN, ROUND_HALF_UP

from app.core.config import settings
from app.services.financial_service import FinancialPlanningSnapshot
from app.services.goal_planning_service import (
    CATEGORY_LABELS,
    GoalCategory,
    GoalPlanningGoal,
    GoalPlanningState,
    GoalPriority,
    emergency_fund_target_amount,
)


ZERO = Decimal("0.00")
CENT = Decimal("0.01")


def _priority_weights() -> dict[GoalPriority, Decimal]:
    return {
        GoalPriority.HIGH: settings.goal_priority_high_weight,
        GoalPriority.MEDIUM: settings.goal_priority_medium_weight,
        GoalPriority.LOW: settings.goal_priority_low_weight,
    }


def _weight_label(value: Decimal) -> str:
    return format(value.normalize(), "f")


@dataclass(frozen=True)
class FundingGoal:
    name: str
    category: GoalCategory
    target_amount: Decimal
    current_amount: Decimal
    proposed_monthly_amount: Decimal
    deadline: date
    priority: GoalPriority


@dataclass(frozen=True)
class GoalAllocation:
    goal: FundingGoal
    one_off_amount: Decimal
    required_monthly_amount: Decimal
    recurring_monthly_amount: Decimal


def _money(value: Decimal) -> str:
    return f"${value:,.2f}"


def _goal_name(goal: GoalPlanningGoal) -> str:
    return str(
        goal.answers.get("goal_title")
        or goal.answers.get("debt_name")
        or CATEGORY_LABELS[goal.category]
    )


def _months_until(deadline: date, as_of: date) -> int:
    months = (deadline.year - as_of.year) * 12 + deadline.month - as_of.month
    if deadline.day > as_of.day:
        months += 1
    return max(months, 1)


def _funding_goal(goal: GoalPlanningGoal) -> FundingGoal | None:
    answers = goal.answers
    if goal.category == GoalCategory.BUDGET:
        return None
    if goal.priority is None:
        raise ValueError(
            f"Planning priority is missing for {_goal_name(goal)}."
        )
    if goal.category == GoalCategory.EMERGENCY_FUND:
        target_amount = emergency_fund_target_amount(answers)
        current_amount = answers["current_amount"]
        proposed_monthly_amount = answers["monthly_contribution"]
    elif goal.category == GoalCategory.DEBT_REPAYMENT:
        target_amount = answers["debt_balance"]
        current_amount = ZERO
        proposed_monthly_amount = (
            answers["minimum_repayment"] + answers["extra_repayment"]
        )
    elif goal.category == GoalCategory.HOME_DEPOSIT:
        direct_target = answers.get("deposit_target", ZERO)
        calculated_target = (
            answers.get("property_price", ZERO)
            * answers.get("deposit_percent", ZERO)
            / Decimal("100")
        )
        target_amount = max(direct_target, calculated_target) + answers.get(
            "cost_buffer", ZERO
        )
        current_amount = answers["current_amount"]
        proposed_monthly_amount = answers["monthly_contribution"]
    elif goal.category == GoalCategory.RETIREMENT:
        target_amount = answers["target_amount"]
        current_amount = answers["current_super"]
        proposed_monthly_amount = answers["regular_contribution"]
    else:
        target_amount = answers["target_amount"]
        current_amount = answers["current_amount"]
        proposed_monthly_amount = answers["monthly_contribution"]

    return FundingGoal(
        name=_goal_name(goal),
        category=goal.category,
        target_amount=target_amount.quantize(CENT, rounding=ROUND_HALF_UP),
        current_amount=current_amount.quantize(CENT, rounding=ROUND_HALF_UP),
        proposed_monthly_amount=proposed_monthly_amount.quantize(
            CENT, rounding=ROUND_HALF_UP
        ),
        deadline=answers["deadline"],
        priority=goal.priority,
    )


def _weighted_capped_allocation(
    total: Decimal,
    caps: list[Decimal],
    weights: list[Decimal],
) -> list[Decimal]:
    allocations = [ZERO for _ in caps]
    remaining = min(max(total, ZERO), sum(caps, ZERO))
    active = {index for index, cap in enumerate(caps) if cap > ZERO}

    while remaining > ZERO and active:
        total_weight = sum((weights[index] for index in active), ZERO)
        capped = []
        for index in active:
            share = remaining * weights[index] / total_weight
            capacity = caps[index] - allocations[index]
            if share >= capacity:
                capped.append(index)
        if not capped:
            for index in active:
                allocations[index] += remaining * weights[index] / total_weight
            remaining = ZERO
            break
        for index in capped:
            capacity = caps[index] - allocations[index]
            allocations[index] += capacity
            remaining -= capacity
            active.remove(index)

    rounded = [
        amount.quantize(CENT, rounding=ROUND_DOWN)
        for amount in allocations
    ]
    target_total = min(max(total, ZERO), sum(caps, ZERO)).quantize(
        CENT, rounding=ROUND_DOWN
    )
    residual = target_total - sum(rounded, ZERO)
    order = sorted(range(len(caps)), key=lambda index: (-weights[index], index))
    while residual >= CENT:
        progressed = False
        for index in order:
            if rounded[index] + CENT <= caps[index]:
                rounded[index] += CENT
                residual -= CENT
                progressed = True
                if residual < CENT:
                    break
        if not progressed:
            break
    return rounded


def calculate_goal_allocations(
    state: GoalPlanningState,
    snapshot: FinancialPlanningSnapshot,
    as_of: date | None = None,
) -> tuple[tuple[GoalAllocation, ...], Decimal, Decimal]:
    effective_date = as_of or date.today()
    missing_priorities = [
        _goal_name(goal)
        for goal in state.goals
        if goal.priority is None
    ]
    if missing_priorities:
        raise ValueError(
            "Every goal needs a planning priority before allocation: "
            + ", ".join(missing_priorities)
        )
    funding_goals = [
        funding_goal
        for goal in state.goals
        if (funding_goal := _funding_goal(goal)) is not None
    ]
    if not funding_goals:
        return (), max(snapshot.ongoing_monthly_surplus, ZERO), max(
            snapshot.one_off_surplus, ZERO
        )

    priority_weights = _priority_weights()
    weights = [priority_weights[goal.priority] for goal in funding_goals]
    remaining_targets = [
        max(goal.target_amount - goal.current_amount, ZERO)
        for goal in funding_goals
    ]
    available_one_off = max(snapshot.one_off_surplus, ZERO)
    one_off_allocations = _weighted_capped_allocation(
        available_one_off,
        remaining_targets,
        weights,
    )
    required_monthly = [
        (
            (remaining_target - one_off_amount)
            / Decimal(_months_until(goal.deadline, effective_date))
        ).quantize(CENT, rounding=ROUND_HALF_UP)
        for goal, remaining_target, one_off_amount in zip(
            funding_goals,
            remaining_targets,
            one_off_allocations,
        )
    ]
    if snapshot.has_financial_records:
        available_recurring = max(snapshot.ongoing_monthly_surplus, ZERO)
        recurring_allocations = _weighted_capped_allocation(
            available_recurring,
            required_monthly,
            weights,
        )
    else:
        # Without verified cash-flow records, the deadline-based requirement is
        # an illustrative planning amount rather than an affordability claim.
        recurring_allocations = required_monthly
        available_recurring = sum(required_monthly, ZERO)

    allocations = tuple(
        GoalAllocation(
            goal=goal,
            one_off_amount=one_off_amount,
            required_monthly_amount=required_amount,
            recurring_monthly_amount=recurring_amount,
        )
        for goal, one_off_amount, required_amount, recurring_amount in zip(
            funding_goals,
            one_off_allocations,
            required_monthly,
            recurring_allocations,
        )
    )
    return (
        allocations,
        available_recurring - sum(recurring_allocations, ZERO),
        available_one_off - sum(one_off_allocations, ZERO),
    )


def build_goal_allocation_context(
    state: GoalPlanningState,
    snapshot: FinancialPlanningSnapshot,
    as_of: date | None = None,
    awaiting_approval: bool = False,
    confirmed_goals_available: bool = False,
) -> str:
    effective_date = as_of or date.today()
    priority_weights = _priority_weights()
    allocations, recurring_unallocated, one_off_unallocated = (
        calculate_goal_allocations(state, snapshot, effective_date)
    )
    if awaiting_approval:
        stage_lines = [
            "Stage: complete recommendation awaiting approval.",
            (
                "Present one complete best recommendation immediately. The AI "
                "has already selected every missing detail using the user's "
                "Preference/Profile memory and financial context. Do not ask the "
                "user to choose or supply a detailed value."
            ),
        ]
    else:
        stage_lines = [
            "Stage: confirmed goal plan.",
            (
                "The user accepted the latest complete recommendation. Present "
                "the agreed goal plan with the exact values below and make clear "
                "that planning is complete."
            ),
        ]
        if confirmed_goals_available:
            stage_lines.append(
                "Confirm that every agreed goal is now available in MyGoals."
            )

    lines = [
        "Goal planning workflow directive:",
        *stage_lines,
        f"Recognized goals to cover in the final response: {len(state.goals)}.",
        (
            "Discuss every recognized goal below in the final response. Do not "
            "omit a goal even when its deadline is longer or its priority is lower."
        ),
        (
            "The following allocation is code-calculated. Do not change, merge, "
            "or invent these amounts."
        ),
        (
            "The priority and planning details below came from explicit user "
            "input where available; otherwise the AI selected them using the "
            "Preference/Profile memory and financial context."
        ),
        (
            "Allocation method: use "
            f"High={_weight_label(priority_weights[GoalPriority.HIGH])}, "
            f"Medium={_weight_label(priority_weights[GoalPriority.MEDIUM])}, "
            f"and Low={_weight_label(priority_weights[GoalPriority.LOW])} "
            "weights, cap each goal at its remaining target or deadline-based "
            "monthly need, then redistribute any excess to the other goals."
        ),
    ]
    if snapshot.has_financial_records:
        lines.extend(
            [
                (
                    "Available ongoing monthly surplus for allocation: "
                    f"{_money(max(snapshot.ongoing_monthly_surplus, ZERO))}."
                ),
                (
                    "Available one-off surplus for allocation: "
                    f"{_money(max(snapshot.one_off_surplus, ZERO))}."
                ),
            ]
        )
    else:
        lines.extend(
            [
                "Verified income, expenses, savings, and available surplus are unavailable.",
                (
                    "Treat every current balance as a conservative assumption and "
                    "every monthly amount as the illustrative requirement for the "
                    "selected deadline, not as proven affordability."
                ),
            ]
        )
    for allocation in allocations:
        goal = allocation.goal
        remaining_target = max(goal.target_amount - goal.current_amount, ZERO)
        lines.extend(
            [
                f"Goal: {goal.name} ({CATEGORY_LABELS[goal.category]}).",
                f"Priority: {goal.priority.value}.",
                f"Target amount: {_money(goal.target_amount)}.",
                f"Current amount: {_money(goal.current_amount)}.",
                (
                    "Remaining target before one-off allocation: "
                    f"{_money(remaining_target)}."
                ),
                (
                    "Recommended one-off allocation: "
                    f"{_money(allocation.one_off_amount)}."
                ),
                (
                    "Monthly amount required after the one-off allocation and "
                    "before interest or returns: "
                    f"{_money(allocation.required_monthly_amount)}."
                ),
                (
                    "Planning monthly amount: "
                    f"{_money(goal.proposed_monthly_amount)}."
                ),
                (
                    "Recommended ongoing monthly allocation: "
                    f"{_money(allocation.recurring_monthly_amount)}."
                ),
                f"Target date: {goal.deadline.isoformat()}.",
            ]
        )

    for goal in (
        goal for goal in state.goals if goal.category == GoalCategory.BUDGET
    ):
        monthly_income = goal.answers.get(
            "monthly_income", snapshot.ongoing_monthly_income
        )
        expenses = (
            goal.answers["fixed_expenses"]
            + goal.answers["variable_expenses"]
        )
        lines.extend(
            [
                "Budget goal is a cash-flow improvement plan, not a funding account.",
                f"Budget monthly income basis: {_money(monthly_income)}.",
                (
                    "Planning fixed plus variable expenses: "
                    f"{_money(expenses)}."
                ),
                (
                    "Target monthly surplus: "
                    f"{_money(goal.answers['target_monthly_surplus'])}."
                ),
            ]
        )

    if snapshot.has_financial_records:
        lines.extend(
            [
                f"Unallocated ongoing monthly surplus: {_money(recurring_unallocated)}.",
                f"Unallocated one-off surplus: {_money(one_off_unallocated)}.",
            ]
        )
    lines.extend(
        [
            (
                "Explain the key trade-off in the recommended amounts and "
                "priorities. When verified surplus is insufficient, explain the "
                "AI-selected adjustment without asking the user for a number."
            ),
            (
                "Keep one-off allocations separate from recurring monthly "
                "allocations."
            ),
        ]
    )
    if awaiting_approval:
        lines.extend(
            [
                (
                    "End with exactly this one question: Does this overall plan "
                    "work for you?"
                ),
                "Do not ask any other question in this response.",
            ]
        )
    else:
        lines.append("Do not ask another question in this response.")
    return "\n".join(lines)
