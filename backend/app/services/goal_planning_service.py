from calendar import monthrange
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from enum import Enum
import re
from typing import Any, Mapping

from app.services.financial_service import FinancialPlanningSnapshot


ZERO = Decimal("0.00")
CENT = Decimal("0.01")
NUMBER_WORDS = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "thirteen": 13,
    "fourteen": 14,
    "fifteen": 15,
    "sixteen": 16,
    "seventeen": 17,
    "eighteen": 18,
    "nineteen": 19,
    "twenty": 20,
}
RELATIVE_DEADLINE_PATTERN = re.compile(
    r"\b(?:within|in)?\s*(?P<number>\d+|"
    + "|".join(NUMBER_WORDS)
    + r")\s+(?P<unit>days?|weeks?|months?|years?)\b",
    re.IGNORECASE,
)


class GoalCategory(str, Enum):
    GENERAL_SAVING = "general_saving"
    EMERGENCY_FUND = "emergency_fund"
    DEBT_REPAYMENT = "debt_repayment"
    HOME_DEPOSIT = "home_deposit"
    RETIREMENT = "retirement"
    BUDGET = "budget"


class GoalPriority(str, Enum):
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class GoalRecommendationStatus(str, Enum):
    NEEDS_RECOMMENDATION = "needs_recommendation"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


@dataclass(frozen=True)
class GoalPlanningGoal:
    category: GoalCategory
    answers: dict[str, Any]
    priority: GoalPriority | None


@dataclass(frozen=True)
class GoalPlanningState:
    goals: tuple[GoalPlanningGoal, ...]
    recommendation_status: GoalRecommendationStatus


CATEGORY_LABELS = {
    GoalCategory.GENERAL_SAVING: "General Saving",
    GoalCategory.EMERGENCY_FUND: "Emergency Fund",
    GoalCategory.DEBT_REPAYMENT: "Debt Repayment",
    GoalCategory.HOME_DEPOSIT: "Home Deposit",
    GoalCategory.RETIREMENT: "Retirement / Super",
    GoalCategory.BUDGET: "Budget / Cash Flow",
}


NUMERIC_FIELDS = frozenset(
    {
        "target_amount",
        "current_amount",
        "monthly_contribution",
        "essential_monthly_expenses",
        "coverage_months",
        "debt_balance",
        "interest_rate",
        "minimum_repayment",
        "extra_repayment",
        "property_price",
        "deposit_percent",
        "deposit_target",
        "cost_buffer",
        "target_age",
        "current_super",
        "regular_contribution",
        "monthly_income",
        "fixed_expenses",
        "variable_expenses",
        "target_monthly_surplus",
    }
)
DATE_FIELDS = frozenset({"deadline"})
TEXT_FIELDS = frozenset({"goal_title", "debt_name", "adjustable_categories"})
ANSWER_FIELDS = tuple(sorted(NUMERIC_FIELDS | DATE_FIELDS | TEXT_FIELDS))

REQUIRED_FIELDS = {
    GoalCategory.GENERAL_SAVING: (
        "goal_title",
        "target_amount",
        "deadline",
        "current_amount",
        "monthly_contribution",
    ),
    GoalCategory.EMERGENCY_FUND: (
        "deadline",
        "current_amount",
        "monthly_contribution",
    ),
    GoalCategory.DEBT_REPAYMENT: (
        "debt_name",
        "debt_balance",
        "minimum_repayment",
        "extra_repayment",
        "deadline",
    ),
    GoalCategory.HOME_DEPOSIT: (
        "current_amount",
        "monthly_contribution",
        "deadline",
    ),
    GoalCategory.RETIREMENT: (
        "target_age",
        "current_super",
        "target_amount",
        "regular_contribution",
        "deadline",
    ),
    GoalCategory.BUDGET: (
        "monthly_income",
        "fixed_expenses",
        "variable_expenses",
        "target_monthly_surplus",
        "deadline",
    ),
}
ZERO_ALLOWED_FIELDS = frozenset(
    {
        "current_amount",
        "current_super",
        "monthly_contribution",
        "minimum_repayment",
        "extra_repayment",
        "cost_buffer",
        "fixed_expenses",
        "monthly_income",
        "variable_expenses",
        "regular_contribution",
    }
)


def _nullable(schema: dict[str, Any]) -> dict[str, Any]:
    return {"anyOf": [schema, {"type": "null"}]}


GOAL_ITEM_PROPERTIES: dict[str, Any] = {
    "category": {
        "type": "string",
        "enum": [category.value for category in GoalCategory],
    },
    "priority": _nullable(
        {
            "type": "string",
            "enum": [priority.value for priority in GoalPriority],
        }
    ),
}
for field in ANSWER_FIELDS:
    field_schema = {"type": "number"} if field in NUMERIC_FIELDS else {"type": "string"}
    GOAL_ITEM_PROPERTIES[field] = _nullable(field_schema)


GOAL_PLANNING_STATE_RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "goals": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": GOAL_ITEM_PROPERTIES,
                "required": list(GOAL_ITEM_PROPERTIES),
            },
        },
        "goal_count": {
            "type": "integer",
            "minimum": 0,
        },
        "recommendation_status": {
            "type": "string",
            "enum": [status.value for status in GoalRecommendationStatus],
        },
    },
    "required": ["goals", "goal_count", "recommendation_status"],
}


def build_goal_state_extraction_prompt(
    conversation_context: str | None,
    user_message: str,
    memory_context: str | None = None,
    financial_context: str | None = None,
) -> str:
    category_fields = [
        (
            f"- {category.value}: "
            + ", ".join(REQUIRED_FIELDS[category])
        )
        for category in GoalCategory
    ]
    return "\n".join(
        [
            "Extract and complete the user's goal-planning state.",
            "Return only a structured object matching the supplied JSON Schema.",
            (
                "Inventory every distinct goal from all user messages before "
                "building the plan. Set goal_count to that inventory size and "
                "return exactly that many goal objects in the user's order."
            ),
            (
                "Multiple purchases or targets are separate goals even when they "
                "share the general_saving category. For example, a computer, a "
                "graphics card, a car, and a house are four separate goals."
            ),
            (
                "Never drop a previously stated goal unless the user explicitly "
                "removes it. An assistant discussing one goal does not remove the "
                "other user-stated goals."
            ),
            (
                "When the earlier conversation contains UI metadata in the form "
                "'Financial goal planning mode: category=<category>', treat that "
                "as the user's explicit category selection for the next goal they "
                "describe, unless the user clearly chooses a different category."
            ),
            "Use these categories and decision-ready fields:",
            *category_fields,
            (
                "An emergency_fund goal needs either a positive direct "
                "target_amount or both positive essential_monthly_expenses and "
                "coverage_months. If confirmed memory identifies an amount as "
                "the direct Emergency Fund target, put it in target_amount and "
                "do not reinterpret or multiply it. A direct target takes "
                "precedence if both representations are available."
            ),
            (
                "A home_deposit goal additionally needs either a positive direct "
                "deposit_target or both a positive property_price and a positive "
                "deposit_percent. Optional fields may be null."
            ),
            (
                "Classify recommendation_status from the current user turn. Use "
                "needs_recommendation when the user introduces or changes goals, "
                "when no complete recommendation has been shown yet, or when the "
                "user answers the assistant's macro-level follow-up. Use accepted "
                "only when the user clearly agrees with the latest complete "
                "recommendation without changing it. Use rejected when the user "
                "disagrees with the latest recommendation and the assistant must "
                "ask a macro-level follow-up next."
            ),
            (
                "For needs_recommendation, produce a complete proposed plan now. "
                "Preserve details explicitly supplied by the user, then decide all "
                "missing amounts, current planning balances, contribution levels, "
                "deadlines, and priorities yourself. Base those decisions on the "
                "Preference and Profile memory text and verified financial context "
                "below. Do not leave a required detail for the user to choose."
            ),
            (
                "For accepted, copy every value and priority from the latest "
                "assistant recommendation exactly so the accepted plan is not "
                "silently regenerated. For rejected, preserve the latest proposal "
                "while the assistant asks about the user's high-level direction."
            ),
            (
                "Do not ask the user for target amounts, current saved amounts, "
                "monthly contributions, income, expenses, dates, rates, balances, "
                "or priorities. These planning details are AI decisions unless the "
                "user volunteered them."
            ),
            (
                "When verified financial records are unavailable, use conservative "
                "and explicit planning assumptions: use zero for an unknown current "
                "balance, do not fabricate income or affordability, and choose an "
                "illustrative target, deadline, and required contribution."
            ),
            (
                f"Today's date is {date.today().isoformat()}. Convert relative "
                "deadlines to ISO YYYY-MM-DD dates. Every required deadline must "
                "be a future date."
            ),
            "Preference and Profile memory text:",
            memory_context or "No Preference or Profile memory is available.",
            "Verified financial context:",
            financial_context or "No verified financial context is available.",
            "Earlier conversation:",
            conversation_context or "No earlier messages.",
            "Current user message:",
            user_message,
        ]
    )


def _raw_decimal_is_usable(value: Any, allow_zero: bool) -> bool:
    amount = _decimal_value(value)
    if amount is None:
        return False
    return amount >= ZERO if allow_zero else amount > ZERO


def _missing_goal_fields(raw_goal: Any) -> list[str]:
    if not isinstance(raw_goal, dict):
        return ["goal object"]
    try:
        category = GoalCategory(str(raw_goal.get("category", "")).strip())
    except ValueError:
        return ["valid category"]

    missing: list[str] = []
    try:
        GoalPriority(raw_goal.get("priority"))
    except (TypeError, ValueError):
        missing.append("priority")

    for field in REQUIRED_FIELDS[category]:
        value = raw_goal.get(field)
        if field in NUMERIC_FIELDS:
            if not _raw_decimal_is_usable(
                value,
                allow_zero=field in ZERO_ALLOWED_FIELDS,
            ):
                missing.append(field)
        elif field in DATE_FIELDS:
            if _date_value(value, date.today()) is None:
                missing.append(field)
        elif _text_value(value) is None:
            missing.append(field)

    if category == GoalCategory.EMERGENCY_FUND:
        has_direct_target = _raw_decimal_is_usable(
            raw_goal.get("target_amount"),
            allow_zero=False,
        )
        has_expenses_and_coverage = _raw_decimal_is_usable(
            raw_goal.get("essential_monthly_expenses"),
            allow_zero=False,
        ) and _raw_decimal_is_usable(
            raw_goal.get("coverage_months"),
            allow_zero=False,
        )
        if not has_direct_target and not has_expenses_and_coverage:
            missing.append(
                "target_amount or essential_monthly_expenses + coverage_months"
            )

    if category == GoalCategory.HOME_DEPOSIT:
        has_direct_target = _raw_decimal_is_usable(
            raw_goal.get("deposit_target"),
            allow_zero=False,
        )
        has_price_and_percent = _raw_decimal_is_usable(
            raw_goal.get("property_price"),
            allow_zero=False,
        ) and _raw_decimal_is_usable(
            raw_goal.get("deposit_percent"),
            allow_zero=False,
        )
        if not has_direct_target and not has_price_and_percent:
            missing.append("deposit_target or property_price + deposit_percent")
    return missing


def goal_state_payload_is_complete(payload: dict[str, Any]) -> bool:
    raw_count = payload.get("goal_count")
    raw_goals = payload.get("goals")
    try:
        recommendation_status = GoalRecommendationStatus(
            payload.get("recommendation_status")
        )
    except (TypeError, ValueError):
        return False
    if not isinstance(raw_count, int) or not isinstance(raw_goals, list):
        return False
    if raw_count != len(raw_goals):
        return False
    if recommendation_status == GoalRecommendationStatus.REJECTED:
        return raw_count > 0 and all(
            isinstance(raw_goal, dict)
            and raw_goal.get("category") in {
                category.value for category in GoalCategory
            }
            for raw_goal in raw_goals
        )
    return raw_count > 0 and not any(
        _missing_goal_fields(raw_goal)
        for raw_goal in raw_goals
    )


def build_goal_state_correction_prompt(
    original_prompt: str,
    payload: dict[str, Any],
) -> str:
    raw_goals = payload.get("goals")
    returned_count = len(raw_goals) if isinstance(raw_goals, list) else 0
    issues: list[str] = []
    if payload.get("goal_count") != returned_count:
        issues.append(
            f"It reported goal_count={payload.get('goal_count')} but returned "
            f"{returned_count} goal objects."
        )
    if payload.get("recommendation_status") not in {
        status.value for status in GoalRecommendationStatus
    }:
        issues.append("recommendation_status is missing or invalid.")
    if isinstance(raw_goals, list):
        for index, raw_goal in enumerate(raw_goals, start=1):
            missing = _missing_goal_fields(raw_goal)
            if missing:
                issues.append(
                    f"Goal {index} is missing usable values for: {', '.join(missing)}."
                )
    if not issues:
        issues.append("The structured goal plan is incomplete.")
    return "\n".join(
        [
            original_prompt,
            "Correction required for the previous structured output:",
            *issues,
            (
                "Re-read every user message, preserve every distinct goal, use "
                "the supplied Preference/Profile and financial context, and return "
                "a complete decision-ready plan with matching counts."
            ),
        ]
    )


def _decimal_value(value: Any) -> Decimal | None:
    if value is None or value == "" or isinstance(value, bool):
        return None
    try:
        amount = Decimal(str(value).replace(",", ""))
    except (InvalidOperation, ValueError):
        return None
    if not amount.is_finite() or amount < ZERO:
        return None
    return amount.quantize(CENT, rounding=ROUND_HALF_UP)


def emergency_fund_target_amount(answers: Mapping[str, Any]) -> Decimal:
    """Return a direct target, otherwise calculate expenses times coverage."""
    direct_target = _decimal_value(answers.get("target_amount"))
    if direct_target is not None and direct_target > ZERO:
        return direct_target
    essential_expenses = _decimal_value(
        answers.get("essential_monthly_expenses")
    )
    coverage_months = _decimal_value(answers.get("coverage_months"))
    if (
        essential_expenses is None
        or essential_expenses <= ZERO
        or coverage_months is None
        or coverage_months <= ZERO
    ):
        raise ValueError(
            "Emergency Fund needs a target amount or expenses and coverage months."
        )
    return (essential_expenses * coverage_months).quantize(
        CENT,
        rounding=ROUND_HALF_UP,
    )


def _text_value(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _add_months(value: date, months: int) -> date:
    month_index = value.year * 12 + value.month - 1 + months
    year, zero_based_month = divmod(month_index, 12)
    month = zero_based_month + 1
    return date(year, month, min(value.day, monthrange(year, month)[1]))


def _date_value(value: Any, as_of: date) -> date | None:
    text = _text_value(value)
    if text is None:
        return None
    try:
        parsed_date = date.fromisoformat(text)
    except ValueError:
        match = RELATIVE_DEADLINE_PATTERN.search(text)
        if match is None:
            return None
        raw_number = match.group("number").lower()
        duration = int(raw_number) if raw_number.isdigit() else NUMBER_WORDS[raw_number]
        unit = match.group("unit").lower()
        if unit.startswith("day"):
            parsed_date = as_of + timedelta(days=duration)
        elif unit.startswith("week"):
            parsed_date = as_of + timedelta(weeks=duration)
        elif unit.startswith("month"):
            parsed_date = _add_months(as_of, duration)
        else:
            parsed_date = _add_months(as_of, duration * 12)
    return parsed_date if parsed_date > as_of else None


def normalize_goal_planning_state(
    payload: dict[str, Any],
    as_of: date | None = None,
) -> GoalPlanningState:
    effective_date = as_of or date.today()
    goals: list[GoalPlanningGoal] = []
    raw_goals = payload.get("goals")
    if not isinstance(raw_goals, list):
        raw_goals = []

    for raw_goal in raw_goals:
        if not isinstance(raw_goal, dict):
            continue
        try:
            category = GoalCategory(str(raw_goal.get("category", "")).strip())
        except ValueError:
            continue

        answers: dict[str, Any] = {}
        for field in ANSWER_FIELDS:
            raw_value = raw_goal.get(field)
            if field in NUMERIC_FIELDS:
                value = _decimal_value(raw_value)
            elif field in DATE_FIELDS:
                value = _date_value(raw_value, effective_date)
            else:
                value = _text_value(raw_value)
            if value is not None:
                answers[field] = value

        try:
            priority = GoalPriority(raw_goal.get("priority"))
        except (TypeError, ValueError):
            priority = None

        goals.append(
            GoalPlanningGoal(
                category=category,
                answers=answers,
                priority=priority,
            )
        )

    try:
        recommendation_status = GoalRecommendationStatus(
            payload.get("recommendation_status")
        )
    except (TypeError, ValueError):
        recommendation_status = GoalRecommendationStatus.NEEDS_RECOMMENDATION

    return GoalPlanningState(
        goals=tuple(goals),
        recommendation_status=recommendation_status,
    )


def _goal_name(goal: GoalPlanningGoal) -> str:
    return str(
        goal.answers.get("goal_title")
        or goal.answers.get("debt_name")
        or CATEGORY_LABELS[goal.category]
    )


def build_goal_dialogue_context(
    state: GoalPlanningState | None,
    snapshot: FinancialPlanningSnapshot,
) -> str | None:
    if state is not None and state.recommendation_status == GoalRecommendationStatus.REJECTED:
        recognized_goals = ", ".join(
            f"{index}. {_goal_name(goal)}"
            for index, goal in enumerate(state.goals, start=1)
        )
        return "\n".join(
            [
                "Goal planning workflow directive:",
                "Stage: recommendation rejected; collect macro direction.",
                f"Recognized goals ({len(state.goals)}): {recognized_goals}.",
                (
                    "Acknowledge the disagreement briefly, then ask exactly one "
                    "concise macro-level question. Ask what the revised plan should "
                    "optimise for at a high level, such as faster progress, more "
                    "monthly flexibility, lower pressure, or a different overall "
                    "goal priority."
                ),
                (
                    "Do not ask for target amounts, saved amounts, contribution "
                    "amounts, balances, income, expenses, rates, dates, coverage "
                    "months, or High/Medium/Low labels. Do not ask more than one "
                    "question and do not propose the revised plan in this response."
                ),
                (
                    "After the user answers, the AI will choose all detailed values "
                    "using Preference/Profile memory and financial context."
                ),
            ]
        )

    if state is None or not state.goals:
        foundation_rule = (
            "Use verified financial records as the affordability basis."
            if snapshot.has_financial_records
            else (
                "No verified financial records are available. Use conservative, "
                "clearly labelled planning assumptions and do not claim that the "
                "illustrative contribution is proven affordable."
            )
        )
        return "\n".join(
            [
                "Goal planning workflow directive:",
                "Stage: complete recommendation awaiting approval.",
                (
                    "Give the user one complete best recommendation immediately. "
                    "Use the Preference/Profile memory and financial context in the "
                    "prompt to decide every detailed amount, deadline, contribution, "
                    "and priority. Do not ask the user for any detailed input."
                ),
                foundation_rule,
                (
                    "Explain the recommendation and its key trade-off, then end with "
                    "exactly this one question: Does this overall plan work for you?"
                ),
            ]
        )

    return None
