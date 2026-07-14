from dataclasses import dataclass
from enum import Enum
import re
from typing import Any


class FinancialRuleIntentName(str, Enum):
    KNOWLEDGE_BASE_STATUS = "knowledge_base_status"
    TAX_BRACKETS = "tax_brackets"
    TAX_CALCULATION = "tax_calculation"
    EMPLOYER_SUPER = "employer_super"
    SUPER_CONTRIBUTION_CAPS = "super_contribution_caps"
    OUT_OF_SCOPE = "out_of_scope"


@dataclass(frozen=True)
class FinancialRuleIntentDefinition:
    name: FinancialRuleIntentName
    semantic_definition: str


@dataclass(frozen=True)
class FinancialRuleIntent:
    intent: FinancialRuleIntentName
    rule_year: str | None
    taxable_income: float | None
    confidence: float


FINANCIAL_RULE_INTENT_DEFINITIONS = (
    FinancialRuleIntentDefinition(
        name=FinancialRuleIntentName.KNOWLEDGE_BASE_STATUS,
        semantic_definition=(
            "The user asks what verified rule years or rule topics "
            "are available in the local knowledge base."
        ),
    ),
    FinancialRuleIntentDefinition(
        name=FinancialRuleIntentName.TAX_BRACKETS,
        semantic_definition=(
            "The user asks for resident income tax brackets, rates, "
            "thresholds, or formulas for a financial year."
        ),
    ),
    FinancialRuleIntentDefinition(
        name=FinancialRuleIntentName.TAX_CALCULATION,
        semantic_definition=(
            "The user asks to estimate income tax for a stated "
            "taxable income amount."
        ),
    ),
    FinancialRuleIntentDefinition(
        name=FinancialRuleIntentName.EMPLOYER_SUPER,
        semantic_definition=(
            "The user asks about employer superannuation guarantee "
            "rates, basis, timing, or obligations."
        ),
    ),
    FinancialRuleIntentDefinition(
        name=FinancialRuleIntentName.SUPER_CONTRIBUTION_CAPS,
        semantic_definition=(
            "The user asks about concessional or non-concessional "
            "superannuation contribution caps."
        ),
    ),
    FinancialRuleIntentDefinition(
        name=FinancialRuleIntentName.OUT_OF_SCOPE,
        semantic_definition=(
            "The user is not asking for a supported Australian tax "
            "or superannuation rule lookup."
        ),
    ),
)

ALLOWED_FINANCIAL_RULE_INTENTS = tuple(
    definition.name.value
    for definition in FINANCIAL_RULE_INTENT_DEFINITIONS
)

FINANCIAL_RULE_INTENT_RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "intent": {
            "type": "string",
            "enum": list(ALLOWED_FINANCIAL_RULE_INTENTS),
        },
        "rule_year": {
            "anyOf": [
                {
                    "type": "string",
                },
                {
                    "type": "null",
                },
            ],
        },
        "taxable_income": {
            "anyOf": [
                {
                    "type": "number",
                },
                {
                    "type": "null",
                },
            ],
        },
        "confidence": {
            "type": "number",
            "minimum": 0,
            "maximum": 1,
        },
    },
    "required": [
        "intent",
        "rule_year",
        "taxable_income",
        "confidence",
    ],
}


def build_financial_rule_intent_prompt(message: str) -> str:
    intent_lines = [
        f"- {definition.name.value}: {definition.semantic_definition}"
        for definition in FINANCIAL_RULE_INTENT_DEFINITIONS
    ]

    return "\n".join(
        [
            (
                "Classify the user's Australian personal finance "
                "rule lookup request."
            ),
            "Use only the allowed intent semantics below.",
            *intent_lines,
            (
                "Return a structured object matching the supplied "
                "JSON Schema. Do not answer the user."
            ),
            (
                "Use null when rule_year or taxable_income is not "
                "present or cannot be inferred from the user's request."
            ),
            (
                "For tax_calculation, taxable_income must be the "
                "numeric annual taxable income if the user supplies one."
            ),
            (
                "Confidence is the model's self-assessed routing "
                "confidence, not a calibrated probability."
            ),
            "User question:",
            message,
        ]
    )


def _normalize_rule_year(rule_year: str) -> str:
    return rule_year.strip().replace("/", "-")


def _normalize_year_pair(
    first_year: str,
    second_year: str,
) -> str:
    first = int(first_year)
    second = int(second_year)

    if second < 100:
        second += (first // 100) * 100

    return f"{first}-{second}"


def _normalize_optional_rule_year(value: Any) -> str | None:
    if value is None:
        return None

    text = str(value).strip()
    if not text:
        return None

    explicit_match = re.search(
        r"(?<!\d)(20\d{2})\s*[-/–]\s*(\d{2}|\d{4})(?!\d)",
        text,
    )

    if explicit_match:
        return _normalize_year_pair(
            explicit_match.group(1),
            explicit_match.group(2),
        )

    single_year_match = re.search(
        r"(?<!\d)(20\d{2})(?!\d)",
        text,
    )

    if single_year_match:
        year = int(single_year_match.group(1))
        return f"{year - 1}-{year}"

    return _normalize_rule_year(text)


def _coerce_optional_float(value: Any) -> float | None:
    if value in {None, ""}:
        return None

    try:
        amount = float(str(value).replace(",", ""))
    except ValueError:
        return None

    if amount <= 0:
        return None

    return amount


def _coerce_confidence(value: Any) -> float:
    try:
        confidence = float(value)
    except (TypeError, ValueError):
        return 0.0

    return max(0.0, min(confidence, 1.0))


def normalize_financial_rule_intent_payload(
    payload: dict[str, Any],
) -> FinancialRuleIntent:
    raw_intent = str(
        payload.get("intent")
        or FinancialRuleIntentName.OUT_OF_SCOPE.value
    ).strip()
    try:
        intent = FinancialRuleIntentName(raw_intent)
    except ValueError:
        intent = FinancialRuleIntentName.OUT_OF_SCOPE

    return FinancialRuleIntent(
        intent=intent,
        rule_year=_normalize_optional_rule_year(
            payload.get("rule_year")
        ),
        taxable_income=_coerce_optional_float(
            payload.get("taxable_income")
        ),
        confidence=_coerce_confidence(
            payload.get("confidence")
        ),
    )
