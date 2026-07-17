from datetime import date


def auth_headers(client, email: str) -> dict[str, str]:
    client.post(
        "/api/auth/register",
        json={"email": email, "password": "Password123"},
    )
    response = client.post(
        "/api/auth/login",
        json={"email": email, "password": "Password123"},
    )
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_financial_assets_and_cash_flows_crud(client):
    headers = auth_headers(client, "finance@example.com")
    asset = client.post(
        "/api/financials/assets",
        headers=headers,
        json={"asset_type": "cash", "name": "Savings", "amount": "1200.50"},
    )
    assert asset.status_code == 201
    asset_id = asset.json()["id"]

    updated_asset = client.put(
        f"/api/financials/assets/{asset_id}",
        headers=headers,
        json={"asset_type": "stocks", "name": "ETF", "amount": "1500.00"},
    )
    assert updated_asset.status_code == 200
    assert updated_asset.json()["asset_type"] == "stocks"

    flow = client.post(
        "/api/financials/cash-flows",
        headers=headers,
        json={
            "flow_type": "income",
            "name": "Salary",
            "amount": "5000.00",
            "date": date.today().isoformat(),
        },
    )
    assert flow.status_code == 201
    flow_id = flow.json()["id"]

    updated_flow = client.put(
        f"/api/financials/cash-flows/{flow_id}",
        headers=headers,
        json={
            "flow_type": "expense",
            "name": "Rent",
            "amount": "2000.00",
            "date": date.today().isoformat(),
        },
    )
    assert updated_flow.status_code == 200
    assert updated_flow.json()["flow_type"] == "expense"

    financials = client.get("/api/financials", headers=headers).json()
    assert len(financials["assets"]) == 1
    assert len(financials["cash_flows"]) == 1
    assert financials["debts"] == []
    assert financials["recurring_cash_flows"] == []

    assert client.delete(
        f"/api/financials/assets/{asset_id}", headers=headers
    ).status_code == 204
    assert client.delete(
        f"/api/financials/cash-flows/{flow_id}", headers=headers
    ).status_code == 204


def test_financial_summary_calculation(client):
    headers = auth_headers(client, "summary@example.com")
    for payload in [
        {"asset_type": "cash", "name": "Savings", "amount": "1000.00"},
        {"asset_type": "stocks", "name": "Shares", "amount": "2500.00"},
    ]:
        client.post("/api/financials/assets", headers=headers, json=payload)

    for payload in [
        {"flow_type": "income", "name": "Salary", "amount": "5000.00"},
        {"flow_type": "expense", "name": "Rent", "amount": "1800.00"},
    ]:
        client.post(
            "/api/financials/cash-flows",
            headers=headers,
            json={**payload, "date": date.today().isoformat()},
        )

    client.post(
        "/api/financials/debts",
        headers=headers,
        json={"debt_type": "car_loan", "name": "Car loan", "balance": "8000.00"},
    )
    client.post(
        "/api/financials/recurring-cash-flows",
        headers=headers,
        json={
            "flow_type": "expense",
            "name": "Subscription",
            "amount": "120.00",
            "frequency": "yearly",
            "start_date": date.today().isoformat(),
        },
    )

    summary = client.get("/api/financials/summary", headers=headers)
    assert summary.status_code == 200
    data = summary.json()
    assert float(data["total_assets"]) == 6700
    assert float(data["total_debts"]) == 8000
    assert float(data["net_worth"]) == -1300
    assert float(data["cash_savings"]) == 4200
    assert float(data["monthly_income"]) == 5000
    assert float(data["monthly_expenses"]) == 1810
    assert float(data["monthly_cash_flow"]) == 3190
    assert data["debt_breakdown"][0]["debt_type"] == "car_loan"
    assert len(data["recent_cash_flows"]) == 2
    assert len(data["cash_savings_trend"]) == 6
    assert float(data["cash_savings_trend"][-1]["amount"]) == 4200


def test_financial_debts_and_recurring_cash_flows_crud(client):
    headers = auth_headers(client, "debt-recurring@example.com")
    debt = client.post(
        "/api/financials/debts",
        headers=headers,
        json={
            "debt_type": "mortgage",
            "name": "Home loan",
            "balance": "600000.00",
            "minimum_payment": "3200.00",
            "interest_rate": "6.20",
        },
    )
    assert debt.status_code == 201
    debt_id = debt.json()["id"]

    updated_debt = client.put(
        f"/api/financials/debts/{debt_id}",
        headers=headers,
        json={"debt_type": "mortgage", "name": "Home loan", "balance": "590000.00"},
    )
    assert updated_debt.status_code == 200
    assert updated_debt.json()["balance"] == "590000.00"
    assert len(client.get("/api/financials/debts", headers=headers).json()) == 1

    flow = client.post(
        "/api/financials/recurring-cash-flows",
        headers=headers,
        json={
            "flow_type": "income",
            "name": "Salary",
            "amount": "2000.00",
            "frequency": "fortnightly",
            "start_date": date.today().isoformat(),
            "category": "salary",
        },
    )
    assert flow.status_code == 201
    flow_id = flow.json()["id"]

    updated_flow = client.put(
        f"/api/financials/recurring-cash-flows/{flow_id}",
        headers=headers,
        json={
            "flow_type": "income",
            "name": "Salary",
            "amount": "2100.00",
            "frequency": "fortnightly",
            "start_date": date.today().isoformat(),
        },
    )
    assert updated_flow.status_code == 200
    assert updated_flow.json()["amount"] == "2100.00"
    assert len(client.get("/api/financials/recurring-cash-flows", headers=headers).json()) == 1

    assert client.delete(f"/api/financials/debts/{debt_id}", headers=headers).status_code == 204
    assert client.delete(f"/api/financials/recurring-cash-flows/{flow_id}", headers=headers).status_code == 204


def test_financial_ownership_and_validation(client):
    first = auth_headers(client, "first-finance@example.com")
    second = auth_headers(client, "second-finance@example.com")
    asset = client.post(
        "/api/financials/assets",
        headers=first,
        json={"asset_type": "cash", "name": "Private", "amount": "10.00"},
    ).json()

    assert client.delete(
        f"/api/financials/assets/{asset['id']}", headers=second
    ).status_code == 404
    cash_flow = client.post(
        "/api/financials/cash-flows",
        headers=first,
        json={
            "flow_type": "expense",
            "name": "Private expense",
            "amount": "10.00",
            "date": date.today().isoformat(),
        },
    ).json()
    assert client.delete(
        f"/api/financials/cash-flows/{cash_flow['id']}", headers=second
    ).status_code == 404
    assert client.post(
        "/api/financials/assets",
        headers=first,
        json={"asset_type": "crypto", "name": "Invalid", "amount": -1},
    ).status_code == 422


def test_debt_and_recurring_cash_flow_crud(client):
    headers = auth_headers(client, "extended-finance@example.com")
    debt = client.post("/api/financials/debts", headers=headers, json={
        "debt_type": "mortgage", "name": "Home loan", "balance": "300000.00",
        "minimum_payment": "2000.00", "interest_rate": "6.25",
    })
    assert debt.status_code == 201
    debt_id = debt.json()["id"]
    updated_debt = client.put(f"/api/financials/debts/{debt_id}", headers=headers, json={
        "debt_type": "mortgage", "name": "Home loan", "balance": "299000.00",
        "minimum_payment": "2000.00", "interest_rate": "6.10",
    })
    assert updated_debt.status_code == 200
    assert float(updated_debt.json()["balance"]) == 299000

    recurring = client.post("/api/financials/recurring-cash-flows", headers=headers, json={
        "flow_type": "income", "name": "Salary", "amount": "1200.00",
        "frequency": "weekly", "start_date": date.today().isoformat(), "category": "salary",
    })
    assert recurring.status_code == 201
    recurring_id = recurring.json()["id"]
    updated_recurring = client.put(
        f"/api/financials/recurring-cash-flows/{recurring_id}", headers=headers,
        json={"flow_type": "income", "name": "Salary", "amount": "5000.00",
              "frequency": "monthly", "start_date": date.today().isoformat()},
    )
    assert updated_recurring.status_code == 200
    financials = client.get("/api/financials", headers=headers).json()
    assert len(financials["debts"]) == 1
    assert len(financials["recurring_cash_flows"]) == 1
    assert client.delete(f"/api/financials/debts/{debt_id}", headers=headers).status_code == 204
    assert client.delete(f"/api/financials/recurring-cash-flows/{recurring_id}", headers=headers).status_code == 204


def test_extended_summary_and_ownership(client):
    first = auth_headers(client, "extended-first@example.com")
    second = auth_headers(client, "extended-second@example.com")
    client.post("/api/financials/assets", headers=first, json={
        "asset_type": "cash", "name": "Savings", "amount": "10000.00",
    })
    debt = client.post("/api/financials/debts", headers=first, json={
        "debt_type": "car_loan", "name": "Car", "balance": "4000.00",
    }).json()
    client.post("/api/financials/recurring-cash-flows", headers=first, json={
        "flow_type": "expense", "name": "Rent", "amount": "1200.00",
        "frequency": "monthly", "start_date": date.today().isoformat(),
    })
    summary = client.get("/api/financials/summary", headers=first).json()
    assert float(summary["total_assets"]) == 10000
    assert float(summary["total_debts"]) == 4000
    assert float(summary["net_worth"]) == 6000
    assert float(summary["cash_savings"]) == 10000
    assert float(summary["monthly_expenses"]) == 1200
    assert summary["debt_breakdown"][0]["debt_type"] == "car_loan"
    assert client.put(f"/api/financials/debts/{debt['id']}", headers=second, json={
        "debt_type": "other", "name": "Not mine", "balance": 1,
    }).status_code == 404
    assert client.post("/api/financials/recurring-cash-flows", headers=first, json={
        "flow_type": "expense", "name": "Invalid", "amount": 1, "frequency": "monthly",
        "start_date": date.today().isoformat(), "end_date": "2000-01-01",
    }).status_code == 422
