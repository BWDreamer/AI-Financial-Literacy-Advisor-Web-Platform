from datetime import date, timedelta


def auth_headers(client, email: str) -> dict[str, str]:
    client.post("/api/auth/register", json={"email": email, "password": "Password123"})
    response = client.post("/api/auth/login", json={"email": email, "password": "Password123"})
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def payload(**overrides):
    data = {"name": "Emergency fund", "category": "savings", "target_amount": "10000.00", "current_amount": "1000.00", "monthly_contribution": "500.00", "target_date": (date.today() + timedelta(days=365)).isoformat(), "priority": 1}
    data.update(overrides)
    return data


def test_goal_crud_contributions_and_summary(client):
    headers = auth_headers(client, "goals@example.com")
    created = client.post("/api/goals", headers=headers, json=payload())
    assert created.status_code == 201
    goal_id = created.json()["id"]
    assert client.get(f"/api/goals/{goal_id}", headers=headers).status_code == 200
    assert len(client.get("/api/goals", headers=headers).json()) == 1
    contribution = client.post(f"/api/goals/{goal_id}/contributions", headers=headers, json={"amount": "250.00"})
    assert contribution.status_code == 201
    assert contribution.json()["goal_id"] == goal_id
    assert float(client.get(f"/api/goals/{goal_id}", headers=headers).json()["current_amount"]) == 1250
    assert len(client.get(f"/api/goals/{goal_id}/contributions", headers=headers).json()) == 1
    updated = client.put(f"/api/goals/{goal_id}", headers=headers, json=payload(name="Holiday", current_amount="1250.00"))
    assert updated.status_code == 200
    assert updated.json()["name"] == "Holiday"
    summary = client.get("/api/goals/summary", headers=headers).json()
    assert summary["total_goals"] == 1
    assert float(summary["total_current_amount"]) == 1250
    assert client.delete(f"/api/goals/{goal_id}", headers=headers).status_code == 204


def test_goals_are_private_and_validate_amounts(client):
    first = auth_headers(client, "goal-first@example.com")
    second = auth_headers(client, "goal-second@example.com")
    goal_id = client.post("/api/goals", headers=first, json=payload()).json()["id"]
    assert client.get(f"/api/goals/{goal_id}", headers=second).status_code == 404
    assert client.get(f"/api/goals/{goal_id}/contributions", headers=second).status_code == 404
    assert client.post(f"/api/goals/{goal_id}/contributions", headers=first, json={"amount": "10000"}).status_code == 422
    assert client.post("/api/goals", headers=first, json=payload(current_amount="11000")).status_code == 422
