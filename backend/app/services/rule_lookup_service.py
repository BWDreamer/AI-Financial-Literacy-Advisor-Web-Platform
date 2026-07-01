import json
import re
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from sqlalchemy.orm import Session

from app.models.financial_rule import FinancialRule
from app.repositories.rule_repository import list_financial_rules


MONEY_PRECISION = Decimal("0.01")
DEFAULT_RULE_YEAR = "2025-2026"
DEFAULT_SUPER_RULE_YEAR = "2025-2026"

TAX_INTENT_KEYWORDS = (
    "tax",
    "taxable",
    "income tax",
    "marginal rate",
    "ato",
    "税",
    "税率",
    "所得税",
    "纳税",
    "缴纳",
    "工资",
    "年薪",
    "收入",
)
KNOWLEDGE_BASE_KEYWORDS = (
    "knowledge base",
    "rules database",
    "rule database",
    "知识库",
    "规则库",
    "更新到哪",
    "覆盖到哪",
    "支持哪些",
)
SUPER_INTENT_KEYWORDS = (
    "super",
    "superannuation",
    "super guarantee",
    "sg",
    "employer contribution",
    "payday super",
    "养老金",
    "退休金",
    "雇主缴纳",
    "雇主供款",
    "养老金比例",
)
SUPER_CONTRIBUTION_CAP_KEYWORDS = (
    "contribution cap",
    "contributions cap",
    "super cap",
    "super caps",
    "concessional",
    "non-concessional",
    "salary sacrifice",
    "extra super",
    "personal contribution",
    "contribute to super",
    "养老金上限",
    "缴纳上限",
    "供款上限",
    "税前养老金",
    "税后养老金",
    "自愿缴纳",
    "额外存",
)
AUSTRALIA_REGION_KEYWORDS = (
    "australia",
    "australian",
    "sydney",
    "nsw",
    "澳大利亚",
    "澳洲",
    "悉尼",
)


def _normalize_rule_year(rule_year: str) -> str:
    return rule_year.strip().replace("/", "-")


def _normalize_region(region: str) -> str:
    return region.strip()


def _contains_any(
    text: str,
    keywords: tuple[str, ...],
) -> bool:
    normalized_text = text.lower()

    return any(
        keyword.lower() in normalized_text
        for keyword in keywords
    )


def _infer_region(message: str) -> str:
    if _contains_any(message, AUSTRALIA_REGION_KEYWORDS):
        return "Australia"

    return "Australia"


def _normalize_year_pair(
    first_year: str,
    second_year: str,
) -> str:
    first = int(first_year)
    second = int(second_year)

    if second < 100:
        second += (first // 100) * 100

    return f"{first}-{second}"


def _infer_rule_year(message: str) -> str:
    explicit_match = re.search(
        r"(?<!\d)(20\d{2})\s*[-/–]\s*(\d{2}|\d{4})(?!\d)",
        message,
    )

    if explicit_match:
        return _normalize_year_pair(
            explicit_match.group(1),
            explicit_match.group(2),
        )

    single_year_match = re.search(
        r"(?<!\d)(20\d{2})(?!\d)",
        message,
    )

    if single_year_match:
        year = int(single_year_match.group(1))
        return f"{year - 1}-{year}"

    return DEFAULT_RULE_YEAR


def _infer_super_rule_year(message: str) -> str:
    if re.search(
        r"(?<!\d)2026\s*[-/–]\s*(27|2027)(?!\d)",
        message,
    ):
        return "2026-2027"

    if "1 july 2026" in message.lower() or "payday super" in message.lower():
        return "2026-2027"

    if "2026年7月1日" in message or "payday super" in message.lower():
        return "2026-2027"

    return DEFAULT_SUPER_RULE_YEAR


def _extract_income(message: str) -> float | None:
    matches = re.findall(
        r"(?<!\d)(\d{1,3}(?:,\d{3})+|\d{4,})(?!\d)",
        message,
    )

    for match in matches:
        value = int(match.replace(",", ""))

        if 1900 <= value <= 2099:
            continue

        return float(value)

    return None


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
        (
            "Sydney/NSW does not use a separate city income-tax "
            "rate for this lookup; use Australian resident ATO "
            "rates."
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
                "Sydney/NSW does not use a separate city income-tax "
                "rate for this lookup; use Australian resident ATO "
                "rates."
            ),
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


def _format_money_amount(value: float | Decimal) -> str:
    return f"${float(value):,.2f}"


def _format_rule_source(
    source_name: str | None,
    source_url: str | None,
) -> str:
    source_label = source_name or "Not provided"
    source_link = source_url or "Not provided"

    return f"Source: {source_label} ({source_link})."


def _format_tax_brackets_answer(
    brackets: list[dict[str, Any]],
) -> str:
    first_bracket = brackets[0]
    lines = [
        (
            f"According to the structured rules knowledge base, "
            f"Australian resident income tax rates for "
            f"{first_bracket['rule_year']} are:"
        ),
    ]

    for bracket in brackets:
        lines.append(
            f"- {bracket['bracket']}: {bracket['formula']}"
        )

    lines.extend(
        [
            (
                "These rates do not include the Medicare levy or "
                "Medicare levy surcharge."
            ),
            (
                "Sydney/NSW does not use a separate city income-tax "
                "rate for this lookup; use Australian resident ATO "
                "rates."
            ),
            _format_rule_source(
                first_bracket["source_name"],
                first_bracket["source_url"],
            ),
            (
                "This is educational information, not personal tax "
                "advice."
            ),
        ]
    )

    return "\n".join(lines)


def _format_tax_lookup_answer(
    lookup_result: dict[str, Any],
) -> str:
    return "\n".join(
        [
            (
                f"According to the structured rules knowledge base, "
                f"for {lookup_result['region']} resident tax rates "
                f"in {lookup_result['rule_year']}:"
            ),
            (
                f"- taxable income "
                f"{_format_money_amount(lookup_result['taxable_income'])} "
                f"falls in the {lookup_result['bracket']} bracket."
            ),
            (
                f"- Marginal rate: "
                f"{lookup_result['marginal_rate_label']}."
            ),
            (
                f"- ATO formula: {lookup_result['formula']}."
            ),
            (
                "- Estimated tax from this bracket formula: "
                f"{_format_money_amount(lookup_result['estimated_tax_excluding_medicare'])}, "
                "excluding Medicare levy."
            ),
            (
                "These rates do not include the Medicare levy or "
                "Medicare levy surcharge."
            ),
            _format_rule_source(
                lookup_result["source_name"],
                lookup_result["source_url"],
            ),
            (
                "This is educational information, not personal tax "
                "advice."
            ),
        ]
    )


def _format_superannuation_answer(
    lookup_result: dict[str, Any],
) -> str:
    lines = [
        (
            f"According to the structured rules knowledge base, "
            f"for {lookup_result['region']} employer super "
            f"guarantee in {lookup_result['rule_year']}:"
        ),
        (
            f"- General super guarantee rate: "
            f"{lookup_result['rate_label']}."
        ),
        f"- Period: {lookup_result['period']}.",
        (
            f"- Earnings basis: "
            f"{lookup_result['earnings_basis']}."
        ),
    ]

    if lookup_result.get("payment_timing"):
        lines.append(
            f"- Payment timing: {lookup_result['payment_timing']}."
        )

    lines.extend(
        [
            _format_rule_source(
                lookup_result["source_name"],
                lookup_result["source_url"],
            ),
            (
                "This is educational information, not personal "
                "financial advice."
            ),
        ]
    )

    return "\n".join(lines)


def _format_super_contribution_caps_answer(
    cap_rules: list[dict[str, Any]],
) -> str:
    first_rule = cap_rules[0]
    lines = [
        (
            f"According to the structured rules knowledge base, "
            f"Australian superannuation contribution caps for "
            f"{first_rule['rule_year']} "
            f"({first_rule['period']}) are:"
        ),
    ]

    for rule in cap_rules:
        lines.append(
            f"- {rule['cap_type'].title()} contributions cap: "
            f"${rule['cap_amount']:,.0f}."
        )
        lines.append(
            f"  Applies to: {rule['applies_to']}."
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
            _format_rule_source(
                first_rule["source_name"],
                first_rule["source_url"],
            ),
            (
                "This is educational information, not personal "
                "financial advice."
            ),
        ]
    )

    return "\n".join(lines)


def _format_missing_rule_answer(
    *,
    region: str,
    rule_year: str,
    rule_label: str,
) -> str:
    return "\n".join(
        [
            (
                f"The local structured rules knowledge base does "
                f"not contain {rule_label} for {region} in "
                f"{rule_year}."
            ),
            (
                "I should not infer a specific rate from model "
                "memory. Please check the official ATO source for "
                "that year."
            ),
        ]
    )


def _format_supported_rule_years_answer(
    db: Session,
    *,
    region: str,
) -> str | None:
    summary = _summarize_supported_rule_years(
        db,
        region=region,
    )

    if not summary:
        return None

    return summary.replace(
        "Use this database for tax and super answers instead of "
        "model memory. If a requested year is missing, say that "
        "the rule is not available in the local rules database "
        "and recommend checking the official ATO source.",
        (
            "For demo-safe rule questions, I answer directly from "
            "this local rules database instead of calling the "
            "external LLM provider."
        ),
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


def build_financial_rule_context(
    db: Session,
    message: str,
) -> str | None:
    """Infer and return verified rules context relevant to a user message."""

    region = _infer_region(message)

    if _contains_any(message, KNOWLEDGE_BASE_KEYWORDS):
        summary = _summarize_supported_rule_years(
            db,
            region=region,
        )

        return summary or None

    if _contains_any(message, SUPER_INTENT_KEYWORDS):
        if _contains_any(
            message,
            SUPER_CONTRIBUTION_CAP_KEYWORDS,
        ):
            cap_context = list_super_contribution_caps(
                db=db,
                region=region,
                rule_year=_infer_super_rule_year(message),
            )

            if cap_context:
                return _format_super_contribution_caps_context(
                    cap_context
                )

            return _format_missing_rule_context(
                region=region,
                rule_year=_infer_super_rule_year(message),
                rule_label="super contribution cap rules",
            )

        super_context = lookup_employer_superannuation_rule(
            db=db,
            region=region,
            rule_year=_infer_super_rule_year(message),
        )

        if super_context is not None:
            return _format_superannuation_context(
                super_context
            )

        return _format_missing_rule_context(
            region=region,
            rule_year=_infer_super_rule_year(message),
            rule_label="employer super guarantee rules",
        )

    if not _contains_any(message, TAX_INTENT_KEYWORDS):
        return None

    rule_year = _infer_rule_year(message)
    income = _extract_income(message)

    if income is not None:
        lookup_result = lookup_tax_bracket(
            db=db,
            region=region,
            rule_year=rule_year,
            income=income,
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


def build_financial_rule_answer(
    db: Session,
    message: str,
) -> str | None:
    """Return a deterministic answer for rule-backed finance questions."""

    region = _infer_region(message)

    if _contains_any(message, KNOWLEDGE_BASE_KEYWORDS):
        return _format_supported_rule_years_answer(
            db,
            region=region,
        )

    if _contains_any(message, SUPER_INTENT_KEYWORDS):
        rule_year = _infer_super_rule_year(message)

        if _contains_any(
            message,
            SUPER_CONTRIBUTION_CAP_KEYWORDS,
        ):
            cap_rules = list_super_contribution_caps(
                db=db,
                region=region,
                rule_year=rule_year,
            )

            if cap_rules:
                return _format_super_contribution_caps_answer(
                    cap_rules
                )

            return _format_missing_rule_answer(
                region=region,
                rule_year=rule_year,
                rule_label="super contribution cap rules",
            )

        super_context = lookup_employer_superannuation_rule(
            db=db,
            region=region,
            rule_year=rule_year,
        )

        if super_context is not None:
            return _format_superannuation_answer(super_context)

        return _format_missing_rule_answer(
            region=region,
            rule_year=rule_year,
            rule_label="employer super guarantee rules",
        )

    if not _contains_any(message, TAX_INTENT_KEYWORDS):
        return None

    rule_year = _infer_rule_year(message)
    income = _extract_income(message)

    if income is not None:
        lookup_result = lookup_tax_bracket(
            db=db,
            region=region,
            rule_year=rule_year,
            income=income,
        )

        if lookup_result is not None:
            return _format_tax_lookup_answer(lookup_result)

    brackets = list_tax_brackets(
        db=db,
        region=region,
        rule_year=rule_year,
    )

    if brackets:
        return _format_tax_brackets_answer(brackets)

    return _format_missing_rule_answer(
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
