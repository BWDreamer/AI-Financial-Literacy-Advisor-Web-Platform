import json
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from sqlalchemy.orm import Session

from app.models.financial_rule import FinancialRule
from app.repositories.rule_repository import list_financial_rules


MONEY_PRECISION = Decimal("0.01")


def _normalize_rule_year(rule_year: str) -> str:
    return rule_year.strip().replace("/", "-")


def _normalize_region(region: str) -> str:
    return region.strip()


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
                f"is: {rule_data['formula']}. These rates do not "
                "include the Medicare levy. Source: "
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
