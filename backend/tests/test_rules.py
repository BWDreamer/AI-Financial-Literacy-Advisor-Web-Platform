import json
from datetime import datetime

from app.models.financial_rule import FinancialRule
from app.schemas.rules import FinancialRuleResponse


ATO_TAX_RATES_URL = (
    "https://www.ato.gov.au/tax-rates-and-codes/"
    "tax-rates-australian-residents"
)
ATO_SUPER_GUARANTEE_URL = (
    "https://www.ato.gov.au/tax-rates-and-codes/"
    "key-superannuation-rates-and-thresholds/"
    "super-guarantee"
)


def create_test_rule(db_session):
    rule = FinancialRule(
        region="Australia",
        category="superannuation",
        rule_year="2025-2026",
        rule_key="employer_super_contribution",
        rule_value="Test superannuation rule.",
        source_name="Australian Taxation Office",
        source_url="https://www.ato.gov.au/",
    )

    db_session.add(rule)
    db_session.commit()
    db_session.refresh(rule)

    return rule


def create_tax_bracket_rules(db_session):
    rules = [
        FinancialRule(
            region="Australia",
            category="tax",
            rule_year="2025-2026",
            rule_key="resident_income_tax_bracket_0_18200",
            rule_value=json.dumps(
                {
                    "bracket_label": "$0 – $18,200",
                    "income_from": 0,
                    "income_to": 18200,
                    "base_tax": 0,
                    "threshold": 0,
                    "marginal_rate": 0,
                    "formula": "Nil",
                    "medicare_levy_included": False,
                }
            ),
            source_name="Australian Taxation Office",
            source_url=ATO_TAX_RATES_URL,
        ),
        FinancialRule(
            region="Australia",
            category="tax",
            rule_year="2025-2026",
            rule_key=(
                "resident_income_tax_bracket_45001_135000"
            ),
            rule_value=json.dumps(
                {
                    "bracket_label": "$45,001 – $135,000",
                    "income_from": 45000.01,
                    "income_to": 135000,
                    "base_tax": 4288,
                    "threshold": 45000,
                    "marginal_rate": 0.30,
                    "formula": (
                        "$4,288 plus 30c for each $1 "
                        "over $45,000"
                    ),
                    "medicare_levy_included": False,
                }
            ),
            source_name="Australian Taxation Office",
            source_url=ATO_TAX_RATES_URL,
        ),
    ]

    db_session.add_all(rules)
    db_session.commit()


def create_superannuation_rule(db_session):
    rule = FinancialRule(
        region="Australia",
        category="superannuation",
        rule_year="2025-2026",
        rule_key="employer_super_contribution",
        rule_value=json.dumps(
            {
                "period": "1 July 2025 – 30 June 2026",
                "general_super_guarantee_percent": 12.00,
                "earnings_basis": "ordinary time earnings",
            }
        ),
        source_name="Australian Taxation Office",
        source_url=ATO_SUPER_GUARANTEE_URL,
    )

    db_session.add(rule)
    db_session.commit()

    return rule


def create_payday_superannuation_rule(db_session):
    rule = FinancialRule(
        region="Australia",
        category="superannuation",
        rule_year="2026-2027",
        rule_key="employer_super_contribution",
        rule_value=json.dumps(
            {
                "period": "1 July 2026 – 30 June 2027",
                "general_super_guarantee_percent": 12.00,
                "earnings_basis": "qualifying earnings",
                "payment_timing": "Payday Super from 1 July 2026",
            }
        ),
        source_name="Australian Taxation Office",
        source_url=ATO_SUPER_GUARANTEE_URL,
    )

    db_session.add(rule)
    db_session.commit()

    return rule


def test_financial_rule_response_supports_structured_rule_value():
    response = FinancialRuleResponse(
        id=1,
        region="Australia",
        category="tax",
        rule_year="2025-2026",
        rule_key="resident_income_tax_bracket_0_18200",
        rule_value={
            "bracket_label": "$0 – $18,200",
            "formula": "Nil",
        },
        source_name="Australian Taxation Office",
        source_url=ATO_TAX_RATES_URL,
        created_at=datetime(2026, 6, 30),
    )

    assert response.rule_value["formula"] == "Nil"


def test_list_financial_rules(client, db_session):
    create_test_rule(db_session)

    response = client.get("/api/rules")

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1
    assert data[0]["region"] == "Australia"
    assert data[0]["category"] == "superannuation"
    assert data[0]["rule_year"] == "2025-2026"


def test_filter_rules_by_category(client, db_session):
    create_test_rule(db_session)

    response = client.get(
        "/api/rules",
        params={
            "category": "superannuation",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1
    assert data[0]["category"] == "superannuation"


def test_filter_rules_is_case_insensitive(
    client,
    db_session,
):
    create_test_rule(db_session)

    response = client.get(
        "/api/rules",
        params={
            "category": "SUPERANNUATION",
            "region": "AUSTRALIA",
            "rule_year": "2025-2026",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1
    assert data[0]["rule_key"] == (
        "employer_super_contribution"
    )


def test_get_rule_by_id(client, db_session):
    rule = create_test_rule(db_session)

    response = client.get(
        f"/api/rules/{rule.id}"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == rule.id
    assert data["region"] == "Australia"
    assert data["source_name"] == (
        "Australian Taxation Office"
    )


def test_missing_rule_returns_not_found(client):
    response = client.get("/api/rules/99999")

    assert response.status_code == 404
    assert response.json()["detail"] == (
        "Financial rule was not found."
    )


def test_unknown_category_returns_empty_list(
    client,
    db_session,
):
    create_test_rule(db_session)

    response = client.get(
        "/api/rules",
        params={
            "category": "insurance",
        },
    )

    assert response.status_code == 200
    assert response.json() == []


def test_tax_bracket_lookup_returns_marginal_rate_and_citation(
    client,
    db_session,
):
    create_tax_bracket_rules(db_session)

    response = client.get(
        "/api/rules/tax-bracket",
        params={
            "region": "Australia",
            "rule_year": "2025/2026",
            "income": 80000,
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["region"] == "Australia"
    assert data["rule_year"] == "2025-2026"
    assert data["taxable_income"] == 80000
    assert data["bracket"] == "$45,001 – $135,000"
    assert data["marginal_rate_percent"] == 30.0
    assert data["marginal_rate_label"] == "30%"
    assert data["estimated_tax_excluding_medicare"] == 14788.0
    assert data["medicare_levy_included"] is False
    assert data["source_name"] == "Australian Taxation Office"
    assert data["source_url"] == ATO_TAX_RATES_URL
    assert "ATO formula" in data["llm_context"]
    assert ATO_TAX_RATES_URL in data["llm_context"]


def test_tax_bracket_lookup_returns_not_found_without_rules(
    client,
):
    response = client.get(
        "/api/rules/tax-bracket",
        params={
            "income": 80000,
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == (
        "No tax bracket rule was found for the "
        "requested region and year."
    )


def test_superannuation_lookup_returns_rate_year_and_source(
    client,
    db_session,
):
    create_superannuation_rule(db_session)

    response = client.get(
        "/api/rules/superannuation/employer-contribution",
        params={
            "region": "Australia",
            "rule_year": "2025-2026",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["region"] == "Australia"
    assert data["rule_year"] == "2025-2026"
    assert data["period"] == "1 July 2025 – 30 June 2026"
    assert data["rate_percent"] == 12.0
    assert data["rate_label"] == "12%"
    assert data["earnings_basis"] == "ordinary time earnings"
    assert data["source_name"] == "Australian Taxation Office"
    assert data["source_url"] == ATO_SUPER_GUARANTEE_URL
    assert "general super guarantee rate is 12%" in (
        data["llm_context"]
    )
    assert ATO_SUPER_GUARANTEE_URL in data["llm_context"]


def test_superannuation_lookup_returns_payday_super_timing(
    client,
    db_session,
):
    create_payday_superannuation_rule(db_session)

    response = client.get(
        "/api/rules/superannuation/employer-contribution",
        params={
            "region": "Australia",
            "rule_year": "2026-2027",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["rule_year"] == "2026-2027"
    assert data["rate_label"] == "12%"
    assert data["earnings_basis"] == "qualifying earnings"
    assert data["payment_timing"] == (
        "Payday Super from 1 July 2026"
    )
