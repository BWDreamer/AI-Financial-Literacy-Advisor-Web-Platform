def test_register_user_successfully(client):
    response = client.post(
        "/api/auth/register",
        json={
            "email": "test@example.com",
            "password": "Password123",
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["email"] == "test@example.com"
    assert data["role"] == "user"
    assert "id" in data
    assert "password" not in data
    assert "password_hash" not in data


def test_duplicate_registration_returns_conflict(client):
    request_data = {
        "email": "duplicate@example.com",
        "password": "Password123",
    }

    first_response = client.post(
        "/api/auth/register",
        json=request_data,
    )

    second_response = client.post(
        "/api/auth/register",
        json=request_data,
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 409

    assert second_response.json()["detail"] == (
        "An account with this email already exists."
    )


def test_login_and_get_current_user(client):
    client.post(
        "/api/auth/register",
        json={
            "email": "login@example.com",
            "password": "Password123",
        },
    )

    login_response = client.post(
        "/api/auth/login",
        json={
            "email": "login@example.com",
            "password": "Password123",
        },
    )

    assert login_response.status_code == 200

    login_data = login_response.json()

    assert login_data["token_type"] == "bearer"
    assert login_data["access_token"]
    assert login_data["expires_in"] > 0

    me_response = client.get(
        "/api/auth/me",
        headers={
            "Authorization": (
                f"Bearer {login_data['access_token']}"
            ),
        },
    )

    assert me_response.status_code == 200
    assert me_response.json()["email"] == "login@example.com"


def test_wrong_password_returns_unauthorized(client):
    client.post(
        "/api/auth/register",
        json={
            "email": "wrong@example.com",
            "password": "Password123",
        },
    )

    response = client.post(
        "/api/auth/login",
        json={
            "email": "wrong@example.com",
            "password": "WrongPassword123",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == (
        "Incorrect email or password."
    )


def test_me_without_token_returns_unauthorized(client):
    response = client.get("/api/auth/me")

    assert response.status_code == 401
    assert response.json()["detail"] == (
        "Authentication credentials were not provided."
    )