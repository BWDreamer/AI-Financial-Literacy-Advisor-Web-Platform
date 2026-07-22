from tests.helpers import register_verified_user


def create_authenticated_headers(client):
    register_verified_user(
        client,
        {
            "email": "profile@example.com",
            "password": "Password123",
        },
    )

    login_response = client.post(
        "/api/auth/login",
        json={
            "email": "profile@example.com",
            "password": "Password123",
        },
    )

    assert login_response.status_code == 200

    access_token = login_response.json()["access_token"]

    return {
        "Authorization": f"Bearer {access_token}",
    }


def test_profile_requires_authentication(client):
    response = client.get("/api/profile")

    assert response.status_code == 401


def test_missing_profile_returns_not_found(client):
    headers = create_authenticated_headers(client)

    response = client.get(
        "/api/profile",
        headers=headers,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == (
        "Financial profile has not been created."
    )


def test_create_profile_successfully(client):
    headers = create_authenticated_headers(client)

    response = client.put(
        "/api/profile",
        headers=headers,
        json={
            "region": "NSW",
            "monthly_income": 5000,
            "fixed_expenses": 2500,
            "current_savings": 10000,
            "initial_savings_target": 20000,
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["region"] == "NSW"
    assert data["monthly_income"] == 5000
    assert data["fixed_expenses"] == 2500
    assert data["current_savings"] == 10000
    assert data["initial_savings_target"] == 20000
    assert "id" in data
    assert "user_id" in data


def test_create_read_and_update_profile(client):
    headers = create_authenticated_headers(client)

    create_response = client.put(
        "/api/profile",
        headers=headers,
        json={
            "region": "NSW",
            "monthly_income": 5000,
            "fixed_expenses": 2500,
            "current_savings": 10000,
            "initial_savings_target": 20000,
        },
    )

    assert create_response.status_code == 200

    created_profile = create_response.json()
    profile_id = created_profile["id"]

    get_response = client.get(
        "/api/profile",
        headers=headers,
    )

    assert get_response.status_code == 200
    assert get_response.json()["id"] == profile_id

    update_response = client.put(
        "/api/profile",
        headers=headers,
        json={
            "region": "VIC",
            "monthly_income": 5500,
            "fixed_expenses": 2600,
            "current_savings": 11000,
            "initial_savings_target": 25000,
        },
    )

    assert update_response.status_code == 200

    updated_profile = update_response.json()

    assert updated_profile["id"] == profile_id
    assert updated_profile["region"] == "VIC"
    assert updated_profile["monthly_income"] == 5500
    assert updated_profile["fixed_expenses"] == 2600
    assert updated_profile["current_savings"] == 11000
    assert updated_profile["initial_savings_target"] == 25000


def test_negative_profile_value_is_rejected(client):
    headers = create_authenticated_headers(client)

    response = client.put(
        "/api/profile",
        headers=headers,
        json={
            "region": "NSW",
            "monthly_income": -100,
            "fixed_expenses": 2500,
            "current_savings": 10000,
            "initial_savings_target": 20000,
        },
    )

    assert response.status_code == 422
