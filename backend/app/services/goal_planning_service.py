from calendar import monthrange
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from enum import Enum
import re
from typing import Any

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


@dataclass(frozen=True)
class GoalQuestion:
    field: str
    prompt: str
    optional: bool = False


@dataclass(frozen=True)
class GoalPlanningGoal:
    category: GoalCategory
    answers: dict[str, Any]
    answered_fields: frozenset[str]
    priority: GoalPriority | None


@dataclass(frozen=True)
class GoalPlanningState:
    goals: tuple[GoalPlanningGoal, ...]
    finished_adding_goals: bool


CATEGORY_LABELS = {
    GoalCategory.GENERAL_SAVING: "General Saving",
    GoalCategory.EMERGENCY_FUND: "Emergency Fund",
    GoalCategory.DEBT_REPAYMENT: "Debt Repayment",
    GoalCategory.HOME_DEPOSIT: "Home Deposit",
    GoalCategory.RETIREMENT: "Retirement / Super",
    GoalCategory.BUDGET: "Budget / Cash Flow",
}


GOAL_QUESTIONS = {
    GoalCategory.GENERAL_SAVING: (
        GoalQuestion("goal_title", "What are you saving for?"),
        GoalQuestion("target_amount", "How much do you want to save?"),
        GoalQuestion("deadline", "When do you want to reach it?"),
        GoalQuestion("current_amount", "How much have you already saved?"),
        GoalQuestion(
            "monthly_contribution",
            "How much can you save each month?",
        ),
    ),
    GoalCategory.EMERGENCY_FUND: (
        GoalQuestion(
            "essential_monthly_expenses",
            "What are your essential monthly expenses?",
        ),
        GoalQuestion("coverage_months", "How many months do you want to cover?"),
        GoalQuestion(
            "deadline",
            "When would you like to complete this buffer?",
        ),
        GoalQuestion("current_amount", "How much do you already have saved?"),
        GoalQuestion(
            "monthly_contribution",
            "How much can you save monthly?",
        ),
    ),
    GoalCategory.DEBT_REPAYMENT: (
        GoalQuestion("debt_name", "What debt do you want to pay off?"),
        GoalQuestion("debt_balance", "What is the current balance?"),
        GoalQuestion(
            "interest_rate",
            "What is the interest rate? You can say you do not know.",
            optional=True,
        ),
        GoalQuestion("minimum_repayment", "What is the minimum repayment?"),
        GoalQuestion(
            "extra_repayment",
            "How much extra can you repay monthly?",
        ),
        GoalQuestion("deadline", "Do you have a preferred payoff deadline?"),
    ),
    GoalCategory.HOME_DEPOSIT: (
        GoalQuestion(
            "property_price",
            "Do you know the target property price?",
            optional=True,
        ),
        GoalQuestion(
            "deposit_percent",
            "What deposit percentage do you want?",
            optional=True,
        ),
        GoalQuestion(
            "deposit_target",
            "If you prefer, what direct deposit target would you use?",
            optional=True,
        ),
        GoalQuestion(
            "cost_buffer",
            "Do you want to include an upfront cost buffer?",
            optional=True,
        ),
        GoalQuestion("current_amount", "How much have you already saved?"),
        GoalQuestion(
            "monthly_contribution",
            "How much can you save monthly?",
        ),
        GoalQuestion("deadline", "When do you want to be ready?"),
    ),
    GoalCategory.RETIREMENT: (
        GoalQuestion("target_age", "What is your target retirement age?"),
        GoalQuestion(
            "current_super",
            "What is your current super or retirement saving?",
        ),
        GoalQuestion(
            "target_amount",
            "What retirement amount do you want to track?",
        ),
        GoalQuestion(
            "regular_contribution",
            "How much is contributed regularly each month?",
        ),
        GoalQuestion("deadline", "What review target date should we use?"),
    ),
    GoalCategory.BUDGET: (
        GoalQuestion("monthly_income", "What is your monthly income?"),
        GoalQuestion("fixed_expenses", "What are your fixed expenses?"),
        GoalQuestion("variable_expenses", "What are your variable expenses?"),
        GoalQuestion(
            "target_monthly_surplus",
            "How much extra do you want to save each month?",
        ),
        GoalQuestion(
            "adjustable_categories",
            "Which spending areas are flexible?",
            optional=True,
        ),
        GoalQuestion("deadline", "What monthly review target date should we use?"),
    ),
}


PRIORITY_QUESTION = GoalQuestion(
    "priority",
    "For this goal, which priority do you choose: High, Medium, or Low?",
)


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
USER_CONFIRMED_FIELDS = (*ANSWER_FIELDS, "priority")


def _nullable(schema: dict[str, Any]) -> dict[str, Any]:
    return {"anyOf": [schema, {"type": "null"}]}


GOAL_ITEM_PROPERTIES: dict[str, Any] = {
    "category": {
        "type": "string",
        "enum": [category.value for category in GoalCategory],
    },
    "answered_fields": {
        "type": "array",
        "items": {
            "type": "string",
            "enum": list(USER_CONFIRMED_FIELDS),
        },
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
        "finished_adding_goals": {"type": "boolean"},
    },
    "required": ["goals", "goal_count", "finished_adding_goals"],
}


def build_goal_state_extraction_prompt(
    conversation_context: str | None,
    user_message: str,
) -> str:
    question_fields = [
        (
            f"- {category.value}: "
            + ", ".join(question.field for question in questions)
        )
        for category, questions in GOAL_QUESTIONS.items()
    ]
    return "\n".join(
        [
            "Extract the user's goal-planning state from this conversation.",
            "Return only a structured object matching the supplied JSON Schema.",
            (
                "Inventory every distinct goal from all user messages before "
                "extracting fields. Set goal_count to that inventory size and "
                "return exactly that many goal objects in the user's order."
            ),
            (
                "Multiple purchases or targets are separate goals even when they "
                "share the general_saving category. For example, a computer, a "
                "graphics card, a car, and a house are four separate goals."
            ),
            (
                "Never drop a previously stated goal unless the user explicitly "
                "removes it. An assistant focusing on one goal does not remove or "
                "deprioritise the other user-stated goals."
            ),
            "Use only these categories and their MyGoals fields:",
            *question_fields,
            "All categories also have the priority field.",
            (
                "Only record facts the user explicitly supplied. Never copy an "
                "amount, date, priority, or suggestion from an assistant message."
            ),
            (
                "Put a field in answered_fields only when the user supplied a "
                "value or explicitly said they do not know or want to skip it."
            ),
            (
                "Never infer, recommend, or preselect priority. Set priority and "
                "include priority in answered_fields only after the user directly "
                "chooses High, Medium, or Low. Otherwise return priority as null."
            ),
            (
                "Map short user answers to the immediately preceding assistant "
                "question for the labelled goal. Keep the latest user answer if "
                "a value was corrected."
            ),
            (
                f"Today's date is {date.today().isoformat()}. Convert explicit "
                "relative deadlines such as 'within two months' or 'in ten years' "
                "to an ISO YYYY-MM-DD deadline from today. If conversion is "
                "uncertain, preserve the user's exact relative phrase in deadline "
                "instead of returning null."
            ),
            (
                "Set finished_adding_goals to true only when the user explicitly "
                "says there are no more goals or that the listed goals are all."
            ),
            "Earlier conversation:",
            conversation_context or "No earlier messages.",
            "Current user message:",
            user_message,
        ]
    )


def goal_state_payload_is_complete(payload: dict[str, Any]) -> bool:
    raw_count = payload.get("goal_count")
    raw_goals = payload.get("goals")
    if not isinstance(raw_count, int) or not isinstance(raw_goals, list):
        return False
    return raw_count == len(raw_goals)


def build_goal_state_correction_prompt(
    original_prompt: str,
    payload: dict[str, Any],
) -> str:
    raw_goals = payload.get("goals")
    returned_count = len(raw_goals) if isinstance(raw_goals, list) else 0
    return "\n".join(
        [
            original_prompt,
            "Correction required for the previous structured output:",
            (
                f"It reported goal_count={payload.get('goal_count')} but returned "
                f"{returned_count} goal objects. Re-read every user message, "
                "preserve every distinct goal, and make these counts equal."
            ),
        ]
    )


def is_goal_planning_follow_up(conversation_context: str | None) -> bool:
    if conversation_context is None:
        return False
    lowered_context = conversation_context.lower()
    question_prompts = [
        question.prompt
        for questions in GOAL_QUESTIONS.values()
        for question in questions
    ]
    question_prompts.extend(
        [
            PRIORITY_QUESTION.prompt,
            "Would you like to add another goal before we work out the allocation?",
            "What direct deposit target should we use",
        ]
    )
    return any(
        prompt.lower() in lowered_context
        for prompt in question_prompts
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
        return date.fromisoformat(text)
    except ValueError:
        match = RELATIVE_DEADLINE_PATTERN.search(text)
        if match is None:
            return None
        raw_number = match.group("number").lower()
        duration = int(raw_number) if raw_number.isdigit() else NUMBER_WORDS[raw_number]
        unit = match.group("unit").lower()
        if unit.startswith("day"):
            return as_of + timedelta(days=duration)
        if unit.startswith("week"):
            return as_of + timedelta(weeks=duration)
        if unit.startswith("month"):
            return _add_months(as_of, duration)
        return _add_months(as_of, duration * 12)


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
        raw_answered_fields = raw_goal.get("answered_fields")
        if not isinstance(raw_answered_fields, list):
            raw_answered_fields = []
        answered_fields = {
            str(field)
            for field in raw_answered_fields
            if str(field) in USER_CONFIRMED_FIELDS
        }
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
                answered_fields.add(field)

        try:
            priority = (
                GoalPriority(raw_goal.get("priority"))
                if "priority" in answered_fields
                else None
            )
        except (TypeError, ValueError):
            priority = None

        goals.append(
            GoalPlanningGoal(
                category=category,
                answers=answers,
                answered_fields=frozenset(answered_fields),
                priority=priority,
            )
        )

    return GoalPlanningState(
        goals=tuple(goals),
        finished_adding_goals=payload.get("finished_adding_goals") is True,
    )


def _has_positive_answer(goal: GoalPlanningGoal, field: str) -> bool:
    value = goal.answers.get(field)
    return isinstance(value, Decimal) and value > ZERO


def _is_question_answered(
    goal: GoalPlanningGoal,
    question: GoalQuestion,
    as_of: date,
) -> bool:
    if question.field not in goal.answered_fields:
        return False
    if question.optional:
        return True

    value = goal.answers.get(question.field)
    if question.field == "current_amount":
        return isinstance(value, Decimal) and value >= ZERO
    if question.field in NUMERIC_FIELDS:
        return isinstance(value, Decimal) and value > ZERO
    if question.field in DATE_FIELDS:
        return isinstance(value, date) and value > as_of
    return isinstance(value, str) and bool(value)


def _next_home_deposit_question(
    goal: GoalPlanningGoal,
    as_of: date,
) -> GoalQuestion | None:
    property_question, percent_question, target_question, *remaining = (
        GOAL_QUESTIONS[GoalCategory.HOME_DEPOSIT]
    )
    has_direct_target = _has_positive_answer(goal, "deposit_target")
    has_price = _has_positive_answer(goal, "property_price")
    has_percent = _has_positive_answer(goal, "deposit_percent")

    if not has_direct_target and not (has_price and has_percent):
        if "property_price" not in goal.answered_fields:
            return property_question
        if has_price and "deposit_percent" not in goal.answered_fields:
            return percent_question
        if "deposit_target" not in goal.answered_fields:
            return target_question
        if not _has_positive_answer(goal, "deposit_target"):
            return GoalQuestion(
                "deposit_target",
                (
                    "What direct deposit target should we use so the home "
                    "deposit can be calculated?"
                ),
            )

    for question in remaining:
        if not _is_question_answered(goal, question, as_of):
            return question
    return None


def _next_question(
    goal: GoalPlanningGoal,
    snapshot: FinancialPlanningSnapshot,
    as_of: date,
) -> GoalQuestion | None:
    if goal.category == GoalCategory.HOME_DEPOSIT:
        question = _next_home_deposit_question(goal, as_of)
        if question is not None:
            return question
    else:
        for question in GOAL_QUESTIONS[goal.category]:
            if (
                goal.category == GoalCategory.BUDGET
                and question.field == "monthly_income"
                and snapshot.ongoing_monthly_income > ZERO
            ):
                continue
            if not _is_question_answered(goal, question, as_of):
                return question

    if goal.priority is None:
        return PRIORITY_QUESTION
    return None


def _goal_name(goal: GoalPlanningGoal) -> str:
    return str(
        goal.answers.get("goal_title")
        or goal.answers.get("debt_name")
        or CATEGORY_LABELS[goal.category]
    )


def build_goal_question_context(
    state: GoalPlanningState | None,
    snapshot: FinancialPlanningSnapshot,
    as_of: date | None = None,
) -> str | None:
    effective_date = as_of or date.today()
    if not snapshot.has_financial_records:
        return "\n".join(
            [
                "Goal planning workflow directive:",
                "Stage: financial foundation required.",
                (
                    "Remind the user to upload a bank statement or transaction "
                    "PDF with the + button in AI Chat before goal questions continue."
                ),
                (
                    "Explain briefly that the PDF supplies the financial basis for "
                    "later questions. Do not ask a goal-detail question this turn."
                ),
            ]
        )

    if state is None or not state.goals:
        return "\n".join(
            [
                "Goal planning workflow directive:",
                "Stage: identify goals.",
                (
                    "Ask exactly this one question: Which goal would you like to "
                    "plan first: general saving, an emergency fund, debt repayment, "
                    "a home deposit, retirement, or a budget?"
                ),
                "Do not ask any additional question in this response.",
            ]
        )

    pending_questions: list[tuple[int, GoalPlanningGoal, GoalQuestion]] = []
    for index, goal in enumerate(state.goals, start=1):
        question = _next_question(goal, snapshot, effective_date)
        if question is not None:
            pending_questions.append((index, goal, question))

    if pending_questions:
        recognized_goals = ", ".join(
            f"{index}. {_goal_name(goal)}"
            for index, goal in enumerate(state.goals, start=1)
        )
        if len(pending_questions) == 1:
            goal_index, _, _ = pending_questions[0]
            stage = (
                f"Stage: collect goal {goal_index} details one question at a time."
            )
            question_rule = (
                "Ask exactly this one labelled question. Do not ask any "
                "additional question in this response."
            )
        else:
            stage = (
                "Stage: collect all incomplete goals in parallel, one next "
                "question per goal."
            )
            question_rule = (
                f"Ask exactly these {len(pending_questions)} numbered, labelled "
                "questions in the same response. Ask one for every listed goal. "
                "Do not omit, merge, or focus on only one goal."
            )

        lines = [
            "Goal planning workflow directive:",
            stage,
            f"Recognized goals ({len(state.goals)}): {recognized_goals}.",
            question_rule,
        ]
        for batch_index, (goal_index, goal, question) in enumerate(
            pending_questions,
            start=1,
        ):
            lines.extend(
                [
                    (
                        f"Question {batch_index} — Goal {goal_index}: "
                        f"{_goal_name(goal)} ({CATEGORY_LABELS[goal.category]})."
                    ),
                    f"Next MyGoals field: {question.field}.",
                    f"Use this exact question: {question.prompt}",
                ]
            )

        lines.append(
            "Keep each question attached to its goal name so a combined user "
            "reply can be mapped back to every goal."
        )
        if any(
            question.field == "priority"
            for _, _, question in pending_questions
        ):
            lines.append(
                "Present High, Medium, and Low neutrally for every priority "
                "question. Do not choose, recommend, or imply any priority."
            )
        else:
            lines.append(
                "Briefly acknowledge the shared trade-off across all recognized "
                "goals, using the user's profile and financial context. Do not "
                "give a final affordability conclusion until every goal is complete."
            )

        for _, goal, question in pending_questions:
            if not (
                goal.category == GoalCategory.BUDGET
                and question.field != "monthly_income"
                and snapshot.ongoing_monthly_income > ZERO
                and "monthly_income" not in goal.answers
            ):
                continue
            lines.append(
                "For the budget goal, reuse the HomePage ongoing monthly income "
                "rather than asking the user to repeat it."
            )
            break
        return "\n".join(lines)

    if not state.finished_adding_goals:
        return "\n".join(
            [
                "Goal planning workflow directive:",
                "Stage: confirm the goal list.",
                (
                    "Ask exactly this one question: Would you like to add another "
                    "goal before we work out the allocation?"
                ),
                "Do not ask any additional question in this response.",
            ]
        )

    return None
