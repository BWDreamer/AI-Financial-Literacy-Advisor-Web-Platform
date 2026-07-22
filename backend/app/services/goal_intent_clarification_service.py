from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from enum import Enum
import re
from typing import Any


CENT = Decimal("0.01")
MEMORY_CATEGORIES = (
    "asset",
    "debt",
    "expense",
    "goal",
    "income",
    "preference",
    "profile",
    "other",
)
BARE_AMOUNT_PATTERN = re.compile(
    r"^\s*(?:AUD\s*)?\$?\s*(?P<amount>\d[\d,]*(?:\.\d{1,2})?)"
    r"\s*(?:AUD|dollars?)?\s*[.!]?\s*$",
    re.IGNORECASE,
)
EMERGENCY_FUND_CONTEXT_PATTERN = re.compile(
    r"\bemergency\s+fund\b",
    re.IGNORECASE,
)
GOAL_CATEGORY_METADATA_PATTERN = re.compile(
    r"Financial goal planning mode:\s*category=(?P<category>[a-z_]+)",
    re.IGNORECASE,
)
EMERGENCY_FUND_AMOUNT_QUESTION_PATTERN = re.compile(
    r"Is\s+\$(?P<amount>\d[\d,]*(?:\.\d{1,2})?)\s+your\s+"
    r"Emergency Fund target amount, or your essential monthly expenses\?",
    re.IGNORECASE,
)
TARGET_ANSWER_PATTERN = re.compile(
    r"\b(?:target|total|first|former)\b|目标|总额|第一|前者",
    re.IGNORECASE,
)
EXPENSE_ANSWER_PATTERN = re.compile(
    r"\b(?:expense|expenses|spending|living costs?|second|latter)\b|"
    r"每月|支出|生活费|第二|后者",
    re.IGNORECASE,
)


class GoalIntentClarificationStatus(str, Enum):
    CLEAR = "clear"
    NEEDS_CLARIFICATION = "needs_clarification"
    RESOLVED = "resolved"


@dataclass(frozen=True)
class GoalIntentClarification:
    status: GoalIntentClarificationStatus
    clarifying_question: str | None = None
    confirmed_fact: str | None = None
    memory_category: str | None = None


GOAL_INTENT_CLARIFICATION_RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "status": {
            "type": "string",
            "enum": [status.value for status in GoalIntentClarificationStatus],
        },
        "clarifying_question": {
            "anyOf": [
                {"type": "string"},
                {"type": "null"},
            ]
        },
        "confirmed_fact": {
            "anyOf": [
                {"type": "string"},
                {"type": "null"},
            ]
        },
        "memory_category": {
            "anyOf": [
                {
                    "type": "string",
                    "enum": list(MEMORY_CATEGORIES),
                },
                {"type": "null"},
            ]
        },
    },
    "required": [
        "status",
        "clarifying_question",
        "confirmed_fact",
        "memory_category",
    ],
}


def _normalized_text(value: Any, maximum_length: int) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = " ".join(value.strip().split())
    if not normalized:
        return None
    return normalized[:maximum_length].rstrip()


def _amount_from_text(value: str) -> Decimal | None:
    match = BARE_AMOUNT_PATTERN.fullmatch(value)
    if match is None:
        return None
    try:
        amount = Decimal(match.group("amount").replace(",", ""))
    except InvalidOperation:
        return None
    if not amount.is_finite() or amount <= 0:
        return None
    return amount.quantize(CENT, rounding=ROUND_HALF_UP)


def _money_without_redundant_cents(amount: Decimal) -> str:
    if amount == amount.to_integral_value():
        return f"${amount:,.0f}"
    return f"${amount:,.2f}"


def build_emergency_fund_amount_question(amount: Decimal) -> str:
    display_amount = _money_without_redundant_cents(amount)
    return (
        f"Is {display_amount} your Emergency Fund target amount, "
        "or your essential monthly expenses?"
    )


def emergency_fund_bare_amount_clarification(
    user_message: str,
    conversation_context: str | None,
) -> GoalIntentClarification | None:
    """Require a meaning before an isolated Emergency Fund amount is used."""
    if conversation_context is None:
        return None
    selected_categories = GOAL_CATEGORY_METADATA_PATTERN.findall(
        conversation_context
    )
    if selected_categories:
        is_emergency_fund = selected_categories[-1].lower() == "emergency_fund"
    else:
        is_emergency_fund = (
            EMERGENCY_FUND_CONTEXT_PATTERN.search(conversation_context)
            is not None
        )
    if not is_emergency_fund:
        return None
    amount = _amount_from_text(user_message)
    if amount is None:
        return None
    return GoalIntentClarification(
        status=GoalIntentClarificationStatus.NEEDS_CLARIFICATION,
        clarifying_question=build_emergency_fund_amount_question(amount),
    )


def pending_emergency_fund_amount(
    last_assistant_message: str | None,
) -> Decimal | None:
    if last_assistant_message is None:
        return None
    match = EMERGENCY_FUND_AMOUNT_QUESTION_PATTERN.search(
        last_assistant_message
    )
    if match is None:
        return None
    try:
        return Decimal(match.group("amount").replace(",", "")).quantize(
            CENT,
            rounding=ROUND_HALF_UP,
        )
    except InvalidOperation:
        return None


def resolve_emergency_fund_amount_answer(
    last_assistant_message: str | None,
    user_message: str,
) -> GoalIntentClarification | None:
    """Resolve common answers to the deterministic amount clarification."""
    amount = pending_emergency_fund_amount(last_assistant_message)
    if amount is None:
        return None
    target_selected = TARGET_ANSWER_PATTERN.search(user_message) is not None
    expenses_selected = EXPENSE_ANSWER_PATTERN.search(user_message) is not None
    if target_selected == expenses_selected:
        return None
    display_amount = f"${amount:,.2f}"
    if target_selected:
        return GoalIntentClarification(
            status=GoalIntentClarificationStatus.RESOLVED,
            confirmed_fact=(
                f"The user's Emergency Fund target amount is {display_amount}."
            ),
            memory_category="goal",
        )
    return GoalIntentClarification(
        status=GoalIntentClarificationStatus.RESOLVED,
        confirmed_fact=(
            "The user's essential monthly expenses for Emergency Fund planning "
            f"are {display_amount}."
        ),
        memory_category="expense",
    )


def build_goal_intent_clarification_prompt(
    conversation_context: str | None,
    user_message: str,
) -> str:
    return "\n".join(
        [
            "Classify whether the user's goal-planning intent is semantically ambiguous.",
            "Return only a structured object matching the supplied JSON Schema.",
            (
                "Use needs_clarification only when a user-supplied amount or statement "
                "has two or more plausible meanings that would change the resulting "
                "goal. Ask exactly one short question that names the alternatives."
            ),
            (
                "An isolated amount in Emergency Fund planning is always ambiguous: "
                "it may be a direct target amount or essential monthly expenses. "
                "Never choose between those meanings without confirmation."
            ),
            (
                "Do not mark normal missing planning details as ambiguous. The planner "
                "is allowed to choose missing balances, contributions, deadlines, "
                "coverage months, and priorities when the user did not supply them."
            ),
            (
                "Use resolved when the current message itself states an unambiguous, "
                "durable user-specific goal fact, or when it clearly answers an earlier "
                "clarification question. For resolved, produce a concise, self-contained "
                "confirmed_fact that includes the subject, semantic meaning, amount when "
                "present, and no unstated assumptions. Choose the matching memory_category."
            ),
            (
                "A vague response such as 'yes', 'okay', or 'that one' does not resolve "
                "alternatives and must never turn an AI-generated recommendation into a "
                "user fact. Never ask whether the user wants a fact saved to memory. Once "
                "the intent is accurate, use resolved so the application saves it "
                "automatically. Use clear when no clarification and no durable user fact "
                "is present, and leave all other fields null."
            ),
            "Earlier goal-planning conversation:",
            conversation_context or "No earlier messages.",
            "Current user message:",
            user_message,
        ]
    )


def normalize_goal_intent_clarification(
    payload: dict[str, Any],
) -> GoalIntentClarification:
    try:
        status = GoalIntentClarificationStatus(payload.get("status"))
    except (TypeError, ValueError):
        return GoalIntentClarification(GoalIntentClarificationStatus.CLEAR)

    if status == GoalIntentClarificationStatus.NEEDS_CLARIFICATION:
        question = _normalized_text(payload.get("clarifying_question"), 500)
        if question is None:
            return GoalIntentClarification(GoalIntentClarificationStatus.CLEAR)
        return GoalIntentClarification(
            status=status,
            clarifying_question=question,
        )

    if status == GoalIntentClarificationStatus.RESOLVED:
        fact = _normalized_text(payload.get("confirmed_fact"), 1000)
        category = payload.get("memory_category")
        if fact is None or category not in MEMORY_CATEGORIES:
            return GoalIntentClarification(GoalIntentClarificationStatus.CLEAR)
        return GoalIntentClarification(
            status=status,
            confirmed_fact=fact,
            memory_category=str(category),
        )

    return GoalIntentClarification(GoalIntentClarificationStatus.CLEAR)
