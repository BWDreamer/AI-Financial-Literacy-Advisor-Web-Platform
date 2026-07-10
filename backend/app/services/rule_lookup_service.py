import json
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.financial_rule import FinancialRule
from app.repositories.rule_repository import list_financial_rules
from app.services.financial_rule_intents import (
    FinancialRuleIntent,
    FinancialRuleIntentName,
)


MONEY_PRECISION = Decimal("0.01")
SUPPORTED_REGION = "Australia"


def _normalize_rule_year(rule_year: str) -> str:
    return rule_year.strip().replace("/", "-")


def _normalize_region(region: str) -> str:
    return region.strip()


def _rule_year_sort_key(rule_year: str) -> tuple[int, int]:
    normalized_rule_year = _normalize_rule_year(rule_year)
    year_parts = normalized_rule_year.split("-", maxsplit=1)

    try:
        start_year = int(year_parts[0])
        end_year = int(year_parts[1]) if len(year_parts) > 1 else start_year
    except ValueError:
        return (0, 0)

    return (start_year, end_year)


def _latest_supported_rule_year(
    db: Session,
    *,
    region: str,
    category: str,
    rule_keys: set[str] | None = None,
    rule_key_prefix: str | None = None,
) -> str | None:
    rules = list_financial_rules(
        db=db,
        region=region,
        category=category,
    )
    supported_years = {
        rule.rule_year
        for rule in rules
        if (
            rule_keys is None
            or rule.rule_key in rule_keys
        )
        and (
            rule_key_prefix is None
            or rule.rule_key.startswith(rule_key_prefix)
        )
    }

    if not supported_years:
        return None

    return max(
        supported_years,
        key=_rule_year_sort_key,
    )


def _latest_tax_rule_year(
    db: Session,
    *,
    region: str,
) -> str | None:
    return _latest_supported_rule_year(
        db,
        region=region,
        category="tax",
        rule_key_prefix="resident_income_tax_bracket_",
    )


def _latest_employer_super_rule_year(
    db: Session,
    *,
    region: str,
) -> str | None:
    return _latest_supported_rule_year(
        db,
        region=region,
        category="superannuation",
        rule_keys={"employer_super_contribution"},
    )


def _latest_super_contribution_cap_rule_year(
    db: Session,
    *,
    region: str,
) -> str | None:
    return _latest_supported_rule_year(
        db,
        region=region,
        category="superannuation",
        rule_keys={
            "concessional_contributions_cap",
            "non_concessional_contributions_cap",
        },
    )


def _parse_rule_value(rule: FinancialRule) -> dict[str, Any]:
    if isinstance(rule.rule_value, dict):
        return rule.rule_value

    try:
        parsed_value = json.loads(rule.rule_value)
    except json.JSONDecodeError as error:
        raise ValueError(
            f"Financial rule {rule.id} does not contain valid JSON."
        ) from error

    if not isinstance(parsed_value, dict):
        raise ValueError(
            f"Financial rule {rule.id} must contain a JSON object."
        )

    return parsed_value


def _to_decimal(value: Any) -> Decimal:
    return Decimal(str(value))


def _round_money(value: Decimal) -> float:
    return float(
        value.quantize(
            MONEY_PRECISION,
            rounding=ROUND_HALF_UP,
        )
    )


def _format_percent(value: Decimal) -> str:
    formatted_value = f"{value:.2f}".rstrip("0").rstrip(".")
    return f"{formatted_value}%"


def _rule_source(rule: FinancialRule) -> dict[str, str | None]:
    return {
        "source_name": rule.source_name,
        "source_url": rule.source_url,
    }


def _tax_bracket_sort_key(rule: FinancialRule) -> Decimal:
    rule_data = _parse_rule_value(rule)

    return _to_decimal(rule_data["income_from"])


def list_tax_brackets(
    db: Session,
    *,
    region: str,
    rule_year: str,
) -> list[dict[str, Any]]:
    """Return all resident income-tax bracket rules for a year."""

    normalized_rule_year = _normalize_rule_year(rule_year)
    normalized_region = _normalize_region(region)
    tax_rules = list_financial_rules(
        db=db,
        region=normalized_region,
        category="tax",
        rule_year=normalized_rule_year,
    )
    bracket_rules = [
        rule
        for rule in tax_rules
        if rule.rule_key.startswith(
            "resident_income_tax_bracket_"
        )
    ]

    return [
        {
            "region": rule.region,
            "rule_year": rule.rule_year,
            "bracket": str(rule_data["bracket_label"]),
            "formula": str(rule_data["formula"]),
            "marginal_rate_percent": float(
                _to_decimal(rule_data["marginal_rate"])
                * Decimal("100")
            ),
            "medicare_levy_included": bool(
                rule_data["medicare_levy_included"]
            ),
            "source_name": rule.source_name,
            "source_url": rule.source_url,
        }
        for rule in sorted(
            bracket_rules,
            key=_tax_bracket_sort_key,
        )
        for rule_data in [_parse_rule_value(rule)]
    ]


def _format_tax_brackets_context(
    brackets: list[dict[str, Any]],
) -> str:
    if not brackets:
        return ""

    first_bracket = brackets[0]
    lines = [
        (
            "Verified financial rule context from the structured "
            "rules knowledge base:"
        ),
        (
            f"Australian resident income tax rates for "
            f"{first_bracket['rule_year']}."
        ),
        (
            "These rates do not include the Medicare levy unless "
            "a bracket explicitly says otherwise."
        ),
        "Tax brackets:",
    ]

    for bracket in brackets:
        lines.append(
            f"- {bracket['bracket']}: {bracket['formula']}"
        )

    lines.extend(
        [
            (
                f"Source: {first_bracket['source_name']} "
                f"({first_bracket['source_url']})."
            ),
            (
                "When answering, cite the source and clearly state "
                "the applicable income year."
            ),
        ]
    )

    return "\n".join(lines)


def _format_tax_lookup_context(
    lookup_result: dict[str, Any],
) -> str:
    return "\n".join(
        [
            (
                "Verified financial rule context from the structured "
                "rules knowledge base:"
            ),
            lookup_result["llm_context"],
            (
                "When answering, cite the source and clearly state "
                "that this is educational information, not personal "
                "tax advice."
            ),
        ]
    )


def _format_superannuation_context(
    lookup_result: dict[str, Any],
) -> str:
    lines = [
        (
            "Verified financial rule context from the structured "
            "rules knowledge base:"
        ),
        lookup_result["llm_context"],
        (
            "When answering, cite the source and clearly state "
            "the applicable financial year."
        ),
    ]

    if lookup_result.get("payment_timing"):
        lines.insert(
            2,
            f"Payment timing: {lookup_result['payment_timing']}.",
        )

    return "\n".join(lines)


def list_super_contribution_caps(
    db: Session,
    *,
    region: str,
    rule_year: str,
) -> list[dict[str, Any]]:
    """Return super contribution cap rules for a region and year."""

    normalized_rule_year = _normalize_rule_year(rule_year)
    normalized_region = _normalize_region(region)
    cap_rules = list_financial_rules(
        db=db,
        region=normalized_region,
        category="superannuation",
        rule_year=normalized_rule_year,
    )

    contribution_cap_rules = [
        rule
        for rule in cap_rules
        if rule.rule_key
        in {
            "concessional_contributions_cap",
            "non_concessional_contributions_cap",
        }
    ]

    return [
        {
            "region": rule.region,
            "rule_year": rule.rule_year,
            "period": str(rule_data["period"]),
            "rule_key": rule.rule_key,
            "cap_type": str(rule_data["cap_type"]),
            "cap_amount": float(
                _to_decimal(rule_data["cap_amount"])
            ),
            "applies_to": str(rule_data["applies_to"]),
            "includes": rule_data.get("includes", []),
            "important_condition": rule_data.get(
                "important_condition"
            ),
            "source_name": rule.source_name,
            "source_url": rule.source_url,
        }
        for rule in sorted(
            contribution_cap_rules,
            key=lambda item: item.rule_key,
        )
        for rule_data in [_parse_rule_value(rule)]
    ]


def _format_super_contribution_caps_context(
    cap_rules: list[dict[str, Any]],
) -> str:
    if not cap_rules:
        return ""

    first_rule = cap_rules[0]
    lines = [
        (
            "Verified financial rule context from the structured "
            "rules knowledge base:"
        ),
        (
            f"Australian superannuation contribution caps for "
            f"{first_rule['rule_year']} "
            f"({first_rule['period']}):"
        ),
    ]

    for rule in cap_rules:
        lines.append(
            f"- {rule['cap_type'].title()} contributions cap: "
            f"${rule['cap_amount']:,.0f}. Applies to "
            f"{rule['applies_to']}."
        )

        if rule["includes"]:
            lines.append(
                "  Includes: "
                f"{', '.join(str(item) for item in rule['includes'])}."
            )

        if rule["important_condition"]:
            lines.append(
                f"  Important condition: "
                f"{rule['important_condition']}"
            )

    lines.extend(
        [
            (
                f"Source: {first_rule['source_name']} "
                f"({first_rule['source_url']})."
            ),
            (
                "When answering, cite the source and clearly state "
                "the applicable financial year. Explain that this is "
                "educational information, not personal financial advice."
            ),
        ]
    )

    return "\n".join(lines)


def _format_missing_rule_context(
    *,
    region: str,
    rule_year: str,
    rule_label: str,
) -> str:
    return "\n".join(
        [
            (
                "Verified financial rule context from the structured "
                "rules knowledge base:"
            ),
            (
                f"The local rules database does not contain "
                f"{rule_label} for {region} in {rule_year}."
            ),
            (
                "Do not infer a specific rate from model memory. "
                "Tell the user this year is not available in the "
                "local rules database and recommend checking the "
                "official ATO source."
            ),
        ]
    )


def _summarize_supported_rule_years(
    db: Session,
    *,
    region: str,
) -> str:
    rules = list_financial_rules(
        db=db,
        region=region,
        category="tax",
    )
    tax_years = sorted(
        {
            rule.rule_year
            for rule in rules
            if rule.rule_key.startswith(
                "resident_income_tax_bracket_"
            )
        }
    )
    super_rules = list_financial_rules(
        db=db,
        region=region,
        category="superannuation",
    )
    super_years = sorted(
        {
            rule.rule_year
            for rule in super_rules
            if rule.rule_key == "employer_super_contribution"
        }
    )
    super_cap_years = sorted(
        {
            rule.rule_year
            for rule in super_rules
            if rule.rule_key
            in {
                "concessional_contributions_cap",
                "non_concessional_contributions_cap",
            }
        }
    )

    if not tax_years and not super_years and not super_cap_years:
        return ""

    lines = [
        (
            "Verified financial rule context from the structured "
            "rules knowledge base:"
        ),
    ]

    if tax_years:
        lines.append(
            "The rules database currently contains Australian "
            "resident income tax brackets for: "
            f"{', '.join(tax_years)}."
        )

    if super_years:
        lines.append(
            "The rules database currently contains Australian "
            "employer super guarantee rules for: "
            f"{', '.join(super_years)}."
        )

    if super_cap_years:
        lines.append(
            "The rules database currently contains Australian "
            "super contribution cap rules for: "
            f"{', '.join(super_cap_years)}."
        )

    lines.append(
        "Use this database for tax and super answers instead of "
        "model memory. If a requested year is missing, say that "
        "the rule is not available in the local rules database "
        "and recommend checking the official ATO source."
    )

    return "\n".join(lines)


def build_financial_rule_context_from_intent(
    db: Session,
    intent: FinancialRuleIntent,
) -> str | None:
    """Return verified rules context for a structured LLM intent."""

    region = SUPPORTED_REGION

    if (
        intent.confidence < settings.rule_intent_confidence_threshold
        or intent.intent == FinancialRuleIntentName.OUT_OF_SCOPE
    ):
        return None

    if intent.intent == FinancialRuleIntentName.KNOWLEDGE_BASE_STATUS:
        summary = _summarize_supported_rule_years(
            db,
            region=region,
        )

        return summary or None

    if intent.intent == FinancialRuleIntentName.SUPER_CONTRIBUTION_CAPS:
        rule_year = intent.rule_year or _latest_super_contribution_cap_rule_year(
            db,
            region=region,
        )
        if rule_year is None:
            return _format_missing_rule_context(
                region=region,
                rule_year="the latest supported year",
                rule_label="super contribution cap rules",
            )

        cap_context = list_super_contribution_caps(
            db=db,
            region=region,
            rule_year=rule_year,
        )

        if cap_context:
            return _format_super_contribution_caps_context(
                cap_context
            )

        return _format_missing_rule_context(
            region=region,
            rule_year=rule_year,
            rule_label="super contribution cap rules",
        )

    if intent.intent == FinancialRuleIntentName.EMPLOYER_SUPER:
        rule_year = intent.rule_year or _latest_employer_super_rule_year(
            db,
            region=region,
        )
        if rule_year is None:
            return _format_missing_rule_context(
                region=region,
                rule_year="the latest supported year",
                rule_label="employer super guarantee rules",
            )

        super_context = lookup_employer_superannuation_rule(
            db=db,
            region=region,
            rule_year=rule_year,
        )

        if super_context is not None:
            return _format_superannuation_context(
                super_context
            )

        return _format_missing_rule_context(
            region=region,
            rule_year=rule_year,
            rule_label="employer super guarantee rules",
        )

    if intent.intent not in {
        FinancialRuleIntentName.TAX_BRACKETS,
        FinancialRuleIntentName.TAX_CALCULATION,
    }:
        return None

    rule_year = intent.rule_year or _latest_tax_rule_year(
        db,
        region=region,
    )
    if rule_year is None:
        return _format_missing_rule_context(
            region=region,
            rule_year="the latest supported year",
            rule_label="resident income tax rates",
        )

    if (
        intent.intent == FinancialRuleIntentName.TAX_CALCULATION
        and intent.taxable_income is not None
    ):
        lookup_result = lookup_tax_bracket(
            db=db,
            region=region,
            rule_year=rule_year,
            income=intent.taxable_income,
        )

        if lookup_result is not None:
            return _format_tax_lookup_context(lookup_result)

    brackets = list_tax_brackets(
        db=db,
        region=region,
        rule_year=rule_year,
    )

    if brackets:
        return _format_tax_brackets_context(brackets)

    return _format_missing_rule_context(
        region=region,
        rule_year=rule_year,
        rule_label="resident income tax rates",
    )


def lookup_tax_bracket(
    db: Session,
    *,
    region: str,
    rule_year: str,
    income: float,
) -> dict[str, Any] | None:
    """Return the resident income-tax rule matching the taxable income."""

    normalized_rule_year = _normalize_rule_year(rule_year)
    normalized_region = _normalize_region(region)
    taxable_income = _to_decimal(income)

    tax_rules = list_financial_rules(
        db=db,
        region=normalized_region,
        category="tax",
        rule_year=normalized_rule_year,
    )

    for rule in tax_rules:
        if not rule.rule_key.startswith(
            "resident_income_tax_bracket_"
        ):
            continue

        rule_data = _parse_rule_value(rule)
        income_from = _to_decimal(rule_data["income_from"])
        income_to_value = rule_data.get("income_to")
        income_to = (
            _to_decimal(income_to_value)
            if income_to_value is not None
            else None
        )

        if taxable_income < income_from:
            continue

        if income_to is not None and taxable_income > income_to:
            continue

        base_tax = _to_decimal(rule_data["base_tax"])
        threshold = _to_decimal(rule_data["threshold"])
        marginal_rate = _to_decimal(rule_data["marginal_rate"])
        taxable_amount_in_bracket = max(
            Decimal("0"),
            taxable_income - threshold,
        )
        estimated_tax = (
            base_tax
            + taxable_amount_in_bracket * marginal_rate
        )
        marginal_rate_percent = marginal_rate * Decimal("100")
        marginal_rate_label = _format_percent(
            marginal_rate_percent
        )
        bracket_label = (
            str(rule_data["bracket_label"])
        )
        source = _rule_source(rule)

        return {
            "region": rule.region,
            "rule_year": rule.rule_year,
            "taxable_income": income,
            "bracket": bracket_label,
            "marginal_rate_percent": float(
                marginal_rate_percent
            ),
            "marginal_rate_label": marginal_rate_label,
            "base_tax": _round_money(base_tax),
            "threshold": _round_money(threshold),
            "estimated_tax_excluding_medicare": (
                _round_money(estimated_tax)
            ),
            "medicare_levy_included": bool(
                rule_data["medicare_levy_included"]
            ),
            "formula": str(rule_data["formula"]),
            "source_name": source["source_name"],
            "source_url": source["source_url"],
            "llm_context": (
                f"For {rule.region} resident tax rates in "
                f"{rule.rule_year}, taxable income "
                f"${_round_money(taxable_income):,.2f} falls in "
                f"the {bracket_label} bracket. The marginal "
                f"rate is {marginal_rate_label}; the ATO formula "
                f"is: {rule_data['formula']}. The estimated tax "
                "from this bracket formula is "
                f"${_round_money(estimated_tax):,.2f}, excluding "
                "Medicare levy. These rates do not include the "
                "Medicare levy. Source: "
                f"{rule.source_name} ({rule.source_url})."
            ),
        }

    return None


def lookup_employer_superannuation_rule(
    db: Session,
    *,
    region: str,
    rule_year: str,
) -> dict[str, Any] | None:
    """Return the employer super guarantee rule for a region and year."""

    normalized_rule_year = _normalize_rule_year(rule_year)
    normalized_region = _normalize_region(region)
    super_rules = list_financial_rules(
        db=db,
        region=normalized_region,
        category="superannuation",
        rule_year=normalized_rule_year,
    )

    for rule in super_rules:
        if rule.rule_key != "employer_super_contribution":
            continue

        rule_data = _parse_rule_value(rule)
        rate_percent = _to_decimal(
            rule_data["general_super_guarantee_percent"]
        )
        rate_label = _format_percent(rate_percent)
        source = _rule_source(rule)

        return {
            "region": rule.region,
            "rule_year": rule.rule_year,
            "period": str(rule_data["period"]),
            "rate_percent": float(rate_percent),
            "rate_label": rate_label,
            "earnings_basis": str(rule_data["earnings_basis"]),
            "payment_timing": rule_data.get("payment_timing"),
            "source_name": source["source_name"],
            "source_url": source["source_url"],
            "llm_context": (
                f"For {rule.region} employer super guarantee in "
                f"{rule.rule_year}, the general super guarantee "
                f"rate is {rate_label} for "
                f"{rule_data['period']}, calculated on "
                f"{rule_data['earnings_basis']}. Source: "
                f"{rule.source_name} ({rule.source_url})."
            ),
        }

    return None
