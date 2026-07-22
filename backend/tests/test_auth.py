from app.models.email_verification import EmailVerificationCode
from app.models.user import User
from tests.helpers import register_verified_user


def registration_payload(
    client,
    *,
    email: str,
    password: str = "Password123",
) -> dict[str, str]:
    sent = client.post(
        "/api/auth/register/verification-code",
        json={"email": email},
    )
    assert sent.status_code == 200
    assert sent.json()["expires_in"] > 0
    return {
        "email": email,
        "password": password,
        "verification_code": client.sent_verification_codes[email],
    }


def login_headers(
    client,
    *,
    email: str,
    password: str = "Password123",
) -> dict[str, str]:
    login = client.post(
        "/api/auth/login",
        json={"email": email, "password": password},
    )
    assert login.status_code == 200
    return {
        "Authorization": f"Bearer {login.json()['access_token']}"
    }


def test_register_requires_and_consumes_email_code(client, db_session):
    payload = registration_payload(client, email="test@example.com")
    code = payload["verification_code"]
    record = db_session.query(EmailVerificationCode).one()
    assert record.code_hash != code
    assert code not in record.code_hash

    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "test@example.com"
    assert data["email_verified_at"]
    assert data["role"] == "user"
    assert "password" not in data
    assert "password_hash" not in data

    db_session.expire_all()
    assert db_session.query(EmailVerificationCode).one().consumed_at
    assert db_session.query(User).one().email_verified_at

    reused = client.post("/api/auth/register", json=payload)
    assert reused.status_code == 409


def test_register_rejects_missing_or_invalid_code(client):
    missing = client.post(
        "/api/auth/register",
        json={
            "email": "missing@example.com",
            "password": "Password123",
        },
    )
    assert missing.status_code == 422

    payload = registration_payload(client, email="invalid@example.com")
    payload["verification_code"] = "000000"
    invalid = client.post("/api/auth/register", json=payload)
    assert invalid.status_code == 400
    assert "invalid or has expired" in invalid.json()["detail"]


def test_verification_code_requests_are_rate_limited(client):
    email = "cooldown@example.com"
    assert client.post(
        "/api/auth/register/verification-code",
        json={"email": email},
    ).status_code == 200
    limited = client.post(
        "/api/auth/register/verification-code",
        json={"email": email},
    )
    assert limited.status_code == 429
    assert int(limited.headers["Retry-After"]) > 0


def test_duplicate_registration_returns_conflict(client):
    payload = registration_payload(client, email="duplicate@example.com")
    assert client.post("/api/auth/register", json=payload).status_code == 201
    duplicate = client.post("/api/auth/register", json=payload)
    assert duplicate.status_code == 409
    assert duplicate.json()["detail"] == (
        "An account with this email already exists."
    )


def test_login_and_get_current_user(client):
    register_verified_user(
        client,
        {"email": "login@example.com", "password": "Password123"},
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
            "Authorization": f"Bearer {login_data['access_token']}",
        },
    )
    assert me_response.status_code == 200
    assert me_response.json()["email"] == "login@example.com"
    assert me_response.json()["email_verified_at"]


def test_wrong_password_returns_unauthorized(client):
    register_verified_user(
        client,
        {"email": "wrong@example.com", "password": "Password123"},
    )
    response = client.post(
        "/api/auth/login",
        json={
            "email": "wrong@example.com",
            "password": "WrongPassword123",
        },
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect email or password."


def test_me_without_token_returns_unauthorized(client):
    response = client.get("/api/auth/me")
    assert response.status_code == 401
    assert response.json()["detail"] == (
        "Authentication credentials were not provided."
    )


def test_email_change_requires_new_email_verification(client, db_session):
    register_verified_user(
        client,
        {"email": "old@example.com", "password": "Password123"},
    )
    headers = login_headers(client, email="old@example.com")
    sent = client.post(
        "/api/auth/email/verification-code",
        headers=headers,
        json={
            "new_email": "new@example.com",
            "current_password": "Password123",
        },
    )
    assert sent.status_code == 200
    code = client.sent_verification_codes["new@example.com"]

    invalid = client.put(
        "/api/auth/email",
        headers=headers,
        json={
            "new_email": "new@example.com",
            "current_password": "Password123",
            "verification_code": "000000",
        },
    )
    assert invalid.status_code == 400

    updated = client.put(
        "/api/auth/email",
        headers=headers,
        json={
            "new_email": "new@example.com",
            "current_password": "Password123",
            "verification_code": code,
        },
    )
    assert updated.status_code == 200
    assert updated.json()["email"] == "new@example.com"
    assert updated.json()["email_verified_at"]

    db_session.expire_all()
    assert db_session.query(User).one().email == "new@example.com"
    assert client.post(
        "/api/auth/login",
        json={
            "email": "new@example.com",
            "password": "Password123",
        },
    ).status_code == 200

    reused = client.put(
        "/api/auth/email",
        headers=headers,
        json={
            "new_email": "another@example.com",
            "current_password": "Password123",
            "verification_code": code,
        },
    )
    assert reused.status_code == 400


def test_email_change_code_requires_current_password(client):
    register_verified_user(
        client,
        {"email": "secure@example.com", "password": "Password123"},
    )
    headers = login_headers(client, email="secure@example.com")
    response = client.post(
        "/api/auth/email/verification-code",
        headers=headers,
        json={
            "new_email": "secure-new@example.com",
            "current_password": "WrongPassword",
        },
    )
    assert response.status_code == 401
    assert "secure-new@example.com" not in client.sent_verification_codes


def test_delete_account_rejects_wrong_password(client):
    register_verified_user(
        client,
        {
            "email": "delete-wrong@example.com",
            "password": "Password123",
        },
    )
    headers = login_headers(client, email="delete-wrong@example.com")
    response = client.request(
        "DELETE",
        "/api/auth/me",
        headers=headers,
        json={"current_password": "WrongPassword"},
    )
    assert response.status_code == 401
    assert client.get("/api/auth/me", headers=headers).status_code == 200


def test_delete_account_removes_user_and_related_data(client):
    register_verified_user(
        client,
        {"email": "delete@example.com", "password": "Password123"},
    )
    headers = login_headers(client, email="delete@example.com")
    client.post(
        "/api/financials/assets",
        headers=headers,
        json={"asset_type": "cash", "name": "Savings", "amount": "100"},
    )
    conversation = client.post(
        "/api/chat/conversations",
        headers=headers,
        json={},
    ).json()
    client.post(
        f"/api/chat/conversations/{conversation['conversation_id']}/messages",
        headers=headers,
        json={"role": "user", "content": "Delete this too"},
    )

    response = client.request(
        "DELETE",
        "/api/auth/me",
        headers=headers,
        json={"current_password": "Password123"},
    )
    assert response.status_code == 204
    assert client.get("/api/auth/me", headers=headers).status_code == 401
