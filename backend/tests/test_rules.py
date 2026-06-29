from app.models.financial_rule import FinancialRule


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