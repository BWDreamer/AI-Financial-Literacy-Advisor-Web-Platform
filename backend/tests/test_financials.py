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

    summary = client.get("/api/financials/summary", headers=headers)
    assert summary.status_code == 200
    data = summary.json()
    assert float(data["net_worth"]) == 3500
    assert float(data["cash_savings"]) == 1000
    assert float(data["monthly_income"]) == 5000
    assert float(data["monthly_expenses"]) == 1800
    assert float(data["monthly_cash_flow"]) == 3200
    assert len(data["recent_cash_flows"]) == 2


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
