def test_compound_interest_calculation(client):
    response = client.post(
        "/api/calculator/compound-interest",
        json={
            "principal": 10000,
            "annual_interest_rate": 5,
            "years": 10,
            "compounds_per_year": 12,
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["principal"] == 10000
    assert data["annual_interest_rate"] == 5
    assert data["years"] == 10
    assert data["compounds_per_year"] == 12
    assert data["final_amount"] == 16470.09
    assert data["interest_earned"] == 6470.09


def test_compound_interest_with_zero_rate(client):
    response = client.post(
        "/api/calculator/compound-interest",
        json={
            "principal": 10000,
            "annual_interest_rate": 0,
            "years": 5,
            "compounds_per_year": 12,
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["final_amount"] == 10000
    assert data["interest_earned"] == 0


def test_goal_monthly_saving_without_interest(client):
    response = client.post(
        "/api/calculator/goal-monthly-saving",
        json={
            "target_amount": 20000,
            "current_amount": 10000,
            "months": 20,
            "annual_interest_rate": 0,
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["target_amount"] == 20000
    assert data["current_amount"] == 10000
    assert data["remaining_amount"] == 10000
    assert data["required_monthly_saving"] == 500
    assert data["additional_saving_required"] is True


def test_completed_goal_requires_no_additional_saving(client):
    response = client.post(
        "/api/calculator/goal-monthly-saving",
        json={
            "target_amount": 10000,
            "current_amount": 12000,
            "months": 12,
            "annual_interest_rate": 0,
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["remaining_amount"] == 0
    assert data["required_monthly_saving"] == 0
    assert data["additional_saving_required"] is False


def test_zero_months_is_rejected(client):
    response = client.post(
        "/api/calculator/goal-monthly-saving",
        json={
            "target_amount": 20000,
            "current_amount": 10000,
            "months": 0,
            "annual_interest_rate": 0,
        },
    )

    assert response.status_code == 422


def test_negative_principal_is_rejected(client):
    response = client.post(
        "/api/calculator/compound-interest",
        json={
            "principal": -100,
            "annual_interest_rate": 5,
            "years": 10,
            "compounds_per_year": 12,
        },
    )

    assert response.status_code == 422